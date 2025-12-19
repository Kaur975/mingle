const express = require("express");
const mongoose = require("mongoose");
const Post = require("../models/Post");
const { authRequired } = require("../middleware/auth");

const router = express.Router();

const TOPICS = ["Politics", "Health", "Sport", "Tech"];

function toInt(value, fallback) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) ? n : fallback;
}

function isValidTopicList(topics) {
  return Array.isArray(topics) && topics.length > 0 && topics.every((t) => TOPICS.includes(t));
}

function computeStatus(expiresAt) {
  return Date.now() < new Date(expiresAt).getTime() ? "Live" : "Expired";
}

async function refreshPostStatusIfNeeded(post) {
  const statusNow = computeStatus(post.expiresAt);
  if (post.status !== statusNow) {
    post.status = statusNow;
    await post.save();
  }
  return statusNow;
}

/**
 * Create a post (Action 2)
 * POST /api/posts
 */
router.post("/", authRequired, async (req, res, next) => {
  try {
    const title = String(req.body.title || "").trim();
    const body = String(req.body.body || "").trim();
    const topics = req.body.topics;

    // You can accept either expiresAt OR expiresInMinutes
    const expiresInMinutes = req.body.expiresInMinutes;
    const expiresAtRaw = req.body.expiresAt;

    if (title.length < 6 || title.length > 120) {
      return res.status(400).json({ error: "Title must be 6–120 characters" });
    }
    if (body.length < 1 || body.length > 2000) {
      return res.status(400).json({ error: "Body must be 1–2000 characters" });
    }
    if (!isValidTopicList(topics)) {
      return res.status(400).json({ error: `Topics must include: ${TOPICS.join(", ")}` });
    }

    let expiresAt;
    if (expiresAtRaw) {
      expiresAt = new Date(expiresAtRaw);
    } else {
      const mins = toInt(expiresInMinutes, 60);
      if (mins < 1 || mins > 60 * 24 * 7) {
        return res.status(400).json({ error: "expiresInMinutes must be 1 to 10080 (7 days)" });
      }
      expiresAt = new Date(Date.now() + mins * 60 * 1000);
    }

    if (Number.isNaN(expiresAt.getTime())) {
      return res.status(400).json({ error: "Invalid expiration time" });
    }

    const post = await Post.create({
      title,
      topics,
      body,
      expiresAt,
      owner: {
        userId: req.user.userId,
        name: req.user.name,
      },
      // status is set by pre-save hook too, but also calculated within the route just to be safe
      status: computeStatus(expiresAt),
    });

    return res.status(201).json(post);
  } catch (err) {
    return next(err);
  }
});

/**
 * Browse posts (Action 3)
 * GET /api/posts?topic=Tech&status=Live&limit=20&skip=0
 */
router.get("/", authRequired, async (req, res, next) => {
  try {
    const topic = req.query.topic ? String(req.query.topic) : null;
    const status = req.query.status ? String(req.query.status) : null;

    
    const limit = Math.min(toInt(req.query.limit, 20), 50);
    const skip = Math.max(toInt(req.query.skip, 0), 0);

    const filter = {};

    if (topic) {
      if (!TOPICS.includes(topic)) {
        return res.status(400).json({ error: `topic must be one of: ${TOPICS.join(", ")}` });
      }
      filter.topics = topic;
    }

    if (status) {
      if (!["Live", "Expired"].includes(status)) {
        return res.status(400).json({ error: "status must be Live or Expired" });
      }
      filter.status = status;
    }

    const posts = await Post.find(filter)
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(limit);

    return res.status(200).json(posts);
  } catch (err) {
    return next(err);
  }
});

/**
 * Get single post
 * GET /api/posts/:id
 */
router.get("/:id", authRequired, async (req, res, next) => {
  try {
    const id = String(req.params.id);

    if (!mongoose.isValidObjectId(id)) {
      return res.status(400).json({ error: "Invalid post id" });
    }

    const post = await Post.findById(id);
    if (!post) {
      return res.status(404).json({ error: "Post not found" });
    }

    await refreshPostStatusIfNeeded(post);

    return res.status(200).json(post);
  } catch (err) {
    return next(err);
  }
});

/**
 * Like a post (Action 4)
 * POST /api/posts/:id/like
 */
router.post("/:id/like", authRequired, async (req, res, next) => {
  try {
    // Verify that a valid post id has been given
    const id = String(req.params.id);
    if (!mongoose.isValidObjectId(id)) {
      return res.status(400).json({ error: "Invalid post id" });
    }

    // Verify the post they are liking exists
    const post = await Post.findById(id);
    if (!post) {
      return res.status(404).json({ error: "Post not found" });
    }

    // Check if user is liking their own post
    if (post.owner.userId.toString() === req.user.userId) {
      return res.status(403).json({ error: "Post owners cannot like their own posts" });
    }

    // Check if the post the user is liking is expired
    const statusNow = await refreshPostStatusIfNeeded(post);
    if (statusNow !== "Live") {
      return res.status(403).json({ error: "Post expired; no further interactions allowed" });
    }

    // Check if the user has already like this post
    const userId = new mongoose.Types.ObjectId(req.user.userId);
    const alreadyLiked = post.likedBy.some((x) => x.equals(userId));
    if (alreadyLiked) {
      return res.status(409).json({ error: "You already liked this post" });
    }
    // If disliked before, remove dislike (toggle)
    const wasDisliked = post.dislikedBy.some((x) => x.equals(userId));
    if (wasDisliked) {
      post.dislikedBy = post.dislikedBy.filter((x) => !x.equals(userId));
      post.dislikesCount = Math.max(0, post.dislikesCount - 1);
    }

    // Increment the likes count on the post
    post.likedBy.push(userId);
    post.likesCount += 1;

    // Attempt to send the API request for adding a like
    await post.save();

    return res.status(200).json({
      message: "Liked",
      likesCount: post.likesCount,
      dislikesCount: post.dislikesCount,
    });
  } catch (err) {
    return next(err);
  }
});


/**
 * Dislike a post (Action 4)
 * POST /api/posts/:id/dislike
 */
router.post("/:id/dislike", authRequired, async (req, res, next) => {
  try {
    // Verify that a valid post id has been given
    const id = String(req.params.id);
    if (!mongoose.isValidObjectId(id)) {
      return res.status(400).json({ error: "Invalid post id" });
    }

    // Verify the post they are disliking exists
    const post = await Post.findById(id);
    if (!post) {
      return res.status(404).json({ error: "Post not found" });
    }

    // Check if user is disliking their own post
    if (post.owner.userId.toString() === req.user.userId) {
      return res.status(403).json({ error: "Post owners cannot dislike their own posts" });
    }

    // Check if the post the user is liking is expired
    const statusNow = await refreshPostStatusIfNeeded(post);
    if (statusNow !== "Live") {
      return res.status(403).json({ error: "Post expired; no further interactions allowed" });
    }

    // Check if the user has already disliked this post
    const userId = new mongoose.Types.ObjectId(req.user.userId);
    const alreadyDisliked = post.dislikedBy.some((x) => x.equals(userId));
    if (alreadyDisliked) {
      return res.status(409).json({ error: "You already disliked this post" });
    }

    // If liked before, remove like (toggle)
    const wasLiked = post.likedBy.some((x) => x.equals(userId));
    if (wasLiked) {
      post.likedBy = post.likedBy.filter((x) => !x.equals(userId));
      post.likesCount = Math.max(0, post.likesCount - 1);
    }

    // Increment the dislikes count on the post
    post.dislikedBy.push(userId);
    post.dislikesCount += 1;

    // Attempt to send the API request for adding a dislike
    await post.save();
    return res.status(200).json({
      message: "Disliked",
      likesCount: post.likesCount,
      dislikesCount: post.dislikesCount,
    });
  } catch (err) {
    return next(err);
  }
});

/**
 * Comment on a post (Action 4)
 * POST /api/posts/:id/comments   body: { text }
 */
router.post("/:id/comments", authRequired, async (req, res, next) => {
  try {
    const id = String(req.params.id);
    if (!mongoose.isValidObjectId(id)) {
      return res.status(400).json({ error: "Invalid post id" });
    }

    const text = String(req.body.text || "").trim();
    if (text.length < 1 || text.length > 500) {
      return res.status(400).json({ error: "Comment must be 1–500 characters" });
    }

    const post = await Post.findById(id);
    if (!post) {
      return res.status(404).json({ error: "Post not found" });
    }

    const statusNow = await refreshPostStatusIfNeeded(post);
    if (statusNow !== "Live") {
      return res.status(403).json({ error: "Post expired; no further interactions allowed" });
    }

    post.comments.push({
      user: {
        userId: req.user.userId,
        name: req.user.name,
      },
      text,
      createdAt: new Date(),
    });

    await post.save();

    return res.status(201).json({
      message: "Comment added",
      commentsCount: post.comments.length,
      comment: post.comments[post.comments.length - 1],
    });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
