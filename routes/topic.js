const express = require("express");
const Post = require("../models/Post");
const { authRequired } = require("../middleware/auth");

const router = express.Router();

const TOPICS = ["Politics", "Health", "Sport", "Tech"];

/**
 * Most active post per topic (Action 5)
 * Definition (per spec): highest likes, then dislikes (tie-breaker: newest)
 * GET /api/topics/:topic/most-active
 */
router.get("/:topic/most-active", authRequired, async (req, res, next) => {
  try {
    const topic = String(req.params.topic);

    if (!TOPICS.includes(topic)) {
      return res.status(400).json({ error: `topic must be one of: ${TOPICS.join(", ")}` });
    }

    const post = await Post.findOne({
      topics: topic,
    })
      .sort({
        likesCount: -1,
        dislikesCount: -1,
        createdAt: -1,
      });

    if (!post) {
      return res.status(404).json({ error: "No posts found for this topic" });
    }

    return res.status(200).json(post);
  } catch (err) {
    return next(err);
  }
});

/**
 * Expired posts history per topic (Action 6)
 * GET /api/topics/:topic/expired?limit=20&skip=0
 */
router.get("/:topic/expired", authRequired, async (req, res, next) => {
  try {
    const topic = String(req.params.topic);

    if (!TOPICS.includes(topic)) {
      return res.status(400).json({ error: `topic must be one of: ${TOPICS.join(", ")}` });
    }

    const limit = Math.min(Number.parseInt(req.query.limit || "20", 10), 50);
    const skip = Math.max(Number.parseInt(req.query.skip || "0", 10), 0);

    const posts = await Post.find({
      topics: topic,
      status: "Expired",
    })
      .sort({ expiresAt: -1 })
      .skip(skip)
      .limit(limit);

    return res.status(200).json(posts);
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
