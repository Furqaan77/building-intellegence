require("dotenv").config();
const { MongoClient } = require("mongodb");

const uri = process.env.MONGODB_URI;
if (!uri || uri.includes("<db_username>") || uri.includes("<db_password>")) {
  console.error("MONGODB_URI is missing or still has placeholders. Edit .env first.");
  process.exit(1);
}

const client = new MongoClient(uri, { serverSelectionTimeoutMS: 8000 });
client
  .connect()
  .then(() => client.db("admin").command({ ping: 1 }))
  .then(() => console.log("Connected to MongoDB Atlas: ping OK"))
  .catch((err) => {
    // Print only the error type/message, never the URI.
    console.error(`Connection failed: ${err.name}: ${err.message}`);
    process.exitCode = 1;
  })
  .finally(() => client.close());
