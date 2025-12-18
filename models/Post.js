const mongoose = require("mongoose");

const TOPICS = ["Politics", "Health", "Sport", "Tech"];

// Embedded comment schema
const CommentSchema = new mongoose.Schema(
  {
    user: {
      userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
      name: { type: String, required: true, trim: true, maxlength: 60 },
    },
    text: { type: String, required: true, trim: true, minlength: 1, maxlength: 500 },
    createdAt: { type: Date, default: Date.now },
  },
  { _id: true }
);

const PostSchema = new mongoose.Schema(
  {
    // Spec: title, topic(s), timestamp, body, expiration, status, owner, likes/dislikes/comments
    title: { 
        type: String, 
        required: true, 
        trim: true, 
        minlength: 2, 
        maxlength: 120 
    },

    topics: {
      type: [String],
      required: true,
      validate: [
        {
          validator: (arr) => Array.isArray(arr) && arr.length > 0,
          message: "At least one topic is required",
        },
        {
          validator: (arr) => arr.every((t) => TOPICS.includes(t)),
          message: `Topics must be one or more of: ${TOPICS.join(", ")}`,
        },
      ],
      index: true,
    },

    body: { type: String, required: true, trim: true, minlength: 1, maxlength: 2000 },

    // Spec: timestamp of registration
    createdAt: { type: Date, default: Date.now, index: true },

    // Spec: expiration time (after which no actions are allowed)
    expiresAt: { type: Date, required: true, index: true },

    // Spec: status Live/Expired
    status: {
      type: String,
      enum: ["Live", "Expired"],
      default: "Live",
      index: true,
    },

    // Spec: post owner info (e.g., name)
    owner: {
      userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
      name: { type: String, required: true, trim: true, maxlength: 60 },
    },

    // Counts (fast sorting for “most active”)
    likesCount: { type: Number, default: 0, min: 0 },
    dislikesCount: { type: Number, default: 0, min: 0 },

    // To prevent multiple votes by same user:
    likedBy: [{ type: mongoose.Schema.Types.ObjectId, ref: "User" }],
    dislikedBy: [{ type: mongoose.Schema.Types.ObjectId, ref: "User" }],

    // Comments list
    comments: { type: [CommentSchema], default: [] },
  },
  { timestamps: true }
);

// Keep status consistent with expiresAt
PostSchema.pre("save", async function () {
  const now = Date.now();
  const exp = new Date(this.expiresAt).getTime();
  this.status = now < exp ? "Live" : "Expired";
});

// Helpful indexes for queries in Actions 3/5/6
PostSchema.index({ topics: 1, status: 1, createdAt: -1 });
PostSchema.index({ topics: 1, likesCount: -1, dislikesCount: -1 });

module.exports = mongoose.model("posts", PostSchema);
