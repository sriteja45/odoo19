# -*- coding: utf-8 -*-

import re

from odoo import models, fields, api


class QevrixaBlogComment(models.Model):
    _name = "qevrixa.blog.comment"
    _description = "Blog Comment"
    _order = "create_date desc"

    # =========================================================
    # BLOG
    # =========================================================

    blog_id = fields.Many2one(
        "qevrixa.blog",
        string="Blog",
        required=True,
        ondelete="cascade",
    )

    # =========================================================
    # USER DETAILS
    # =========================================================

    user_id = fields.Many2one(
        "res.users",
        string="User",
        readonly=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        readonly=True,
    )

    name = fields.Char(
        string="Name",
        required=True,
    )

    email = fields.Char(
        string="Email",
    )

    # =========================================================
    # COMMENT
    # =========================================================

    comment = fields.Text(
        string="Comment",
        required=True,
    )

    # =========================================================
    # COMMENT LIKE / DISLIKE
    # =========================================================

    likes = fields.Integer(
        string="Likes",
        default=0,
    )

    dislikes = fields.Integer(
        string="Dislikes",
        default=0,
    )

    # =========================================================
    # COMMENT REPORT
    # =========================================================

    reported = fields.Boolean(
        string="Reported",
        default=False,
    )

    report_reason = fields.Text(
        string="Report Reason",
    )

    report_count = fields.Integer(
        string="Report Count",
        default=0,
    )

    # =========================================================
    # AUTO MODERATION
    # =========================================================

    blocked = fields.Boolean(
        string="Blocked",
        default=False,
        index=True,
        help="Automatically blocked comment.",
    )

    block_reason = fields.Text(
        string="Block Reason",
        readonly=True,
        help="Reason why the comment was automatically blocked.",
    )

    moderation_status = fields.Selection(
        [
            ("approved", "Approved"),
            ("blocked", "Blocked"),
        ],
        string="Moderation Status",
        default="approved",
        required=True,
        index=True,
    )

    # =========================================================
    # HARMFUL WORDS
    # =========================================================

    HARMFUL_KEYWORDS = [
        "kill",
        "killing",
        "murder",
        "suicide",
        "self harm",
        "self-harm",
        "bomb",
        "explosive",
        "terrorist",
        "terrorism",
        "weapon",
        "weapons",
        "shoot",
        "shooting",
        "stab",
        "stabbing",
        "violence",
        "violent",
        "blood",
        "rape",
        "sexual abuse",
        "child abuse",
        "abuse",
        "threat",
        "threaten",
        "death threat",
        "harm you",
        "hurt you",
    ]

    # =========================================================
    # SUSPICIOUS / SPAM WORDS
    # =========================================================

    SUSPICIOUS_KEYWORDS = [
        "buy now",
        "click here",
        "free money",
        "make money fast",
        "earn money",
        "easy money",
        "crypto investment",
        "bitcoin investment",
        "investment opportunity",
        "double your money",
        "100% guaranteed",
        "guaranteed profit",
        "winner",
        "you won",
        "claim prize",
        "claim your prize",
        "lottery",
        "casino",
        "betting",
        "viagra",
        "porn",
        "adult content",
        "xxx",
        "telegram",
        "whatsapp me",
        "contact me for offer",
        "limited offer",
        "special offer",
        "promote my product",
        "visit my website",
    ]

    # =========================================================
    # HELPER - NORMALIZE TEXT
    # =========================================================

    @api.model
    def _normalize_moderation_text(self, text):
        """
        Normalize comment text before moderation.
        """

        if not text:
            return ""

        text = str(text).lower()

        # Remove HTML
        text = re.sub(
            r"<[^>]+>",
            " ",
            text
        )

        # Normalize spaces
        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # =========================================================
    # HELPER - FIND KEYWORD
    # =========================================================

    @api.model
    def _contains_keyword(self, text, keywords):
        """
        Check whether normalized text contains
        any configured keyword.
        """

        if not text:
            return False, ""

        for keyword in keywords:

            keyword = self._normalize_moderation_text(
                keyword
            )

            if not keyword:
                continue

            # Word/phrase boundary check
            pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"

            if re.search(pattern, text, flags=re.IGNORECASE):
                return True, keyword

        return False, ""

    # =========================================================
    # HELPER - SUSPICIOUS URL CHECK
    # =========================================================

    @api.model
    def _check_suspicious_links(self, text):
        """
        Detect excessive or suspicious links.
        A normal product/reference link is allowed.
        """

        if not text:
            return False, ""

        urls = re.findall(
            r"https?://[^\s]+",
            text,
            flags=re.IGNORECASE
        )

        # Too many links in one comment
        if len(urls) >= 4:
            return True, "Too many external links"

        suspicious_domains = [
            "bit.ly",
            "tinyurl.com",
            "t.co",
            "grabify",
            "iplogger",
            "freegift",
            "clickme",
        ]

        for url in urls:

            for domain in suspicious_domains:

                if domain in url.lower():
                    return True, (
                        "Suspicious external link"
                    )

        return False, ""

    # =========================================================
    # HELPER - REPEATED CHARACTERS / SPAM
    # =========================================================

    @api.model
    def _check_spam_pattern(self, text):
        """
        Detect obvious spam patterns.
        """

        if not text:
            return False, ""

        # Same character repeated many times
        if re.search(
            r"(.)\1{8,}",
            text
        ):
            return True, "Repeated character spam"

        # Same word repeated many times
        words = text.split()

        if len(words) >= 8:

            word_count = {}

            for word in words:

                clean_word = re.sub(
                    r"[^a-z0-9]",
                    "",
                    word.lower()
                )

                if not clean_word:
                    continue

                word_count[clean_word] = (
                    word_count.get(clean_word, 0) + 1
                )

            for word, count in word_count.items():

                if count >= 6:
                    return True, (
                        "Repeated word spam"
                    )

        return False, ""

    # =========================================================
    # HELPER - UNRELATED COMMENT CHECK
    # =========================================================

    @api.model
    def _check_unrelated_comment(self, blog, comment_text):
        """
        Basic relevance check.

        The comment is considered unrelated when:
        - Blog has meaningful title/content keywords
        - Comment is long enough to evaluate
        - No meaningful blog keyword is present
        """

        if not blog or not comment_text:
            return False, ""

        blog_text = ""

        if blog.name:
            blog_text += " " + blog.name

        if "short_description" in blog._fields:
            blog_text += " " + (
                blog.short_description or ""
            )

        if "content" in blog._fields:
            blog_text += " " + (
                blog.content or ""
            )

        blog_text = self._normalize_moderation_text(
            blog_text
        )

        comment_text = self._normalize_moderation_text(
            comment_text
        )

        if not blog_text or not comment_text:
            return False, ""

        # Very short comments are not automatically
        # considered unrelated.
        comment_words = [
            word
            for word in re.findall(
                r"[a-zA-Z0-9]+",
                comment_text
            )
            if len(word) >= 4
        ]

        if len(comment_words) < 4:
            return False, ""

        blog_words = set(
            word
            for word in re.findall(
                r"[a-zA-Z0-9]+",
                blog_text
            )
            if len(word) >= 4
        )

        if not blog_words:
            return False, ""

        # Common English words should not be used
        # as relevance signals.
        stop_words = {
            "this",
            "that",
            "with",
            "from",
            "have",
            "your",
            "about",
            "what",
            "when",
            "where",
            "which",
            "will",
            "would",
            "could",
            "should",
            "there",
            "their",
            "they",
            "them",
            "than",
            "then",
            "also",
            "very",
            "more",
            "some",
            "good",
            "nice",
            "really",
            "just",
            "like",
            "this",
            "blog",
            "post",
            "article",
        }

        meaningful_comment_words = [
            word
            for word in comment_words
            if word not in stop_words
        ]

        if len(meaningful_comment_words) < 4:
            return False, ""

        matched_words = []

        for word in meaningful_comment_words:

            if word in blog_words:
                matched_words.append(word)

        # If there is at least one meaningful matching
        # keyword, allow the comment.
        if matched_words:
            return False, ""

        return True, (
            "Comment appears unrelated to the blog topic"
        )

    # =========================================================
    # AUTO MODERATION
    # =========================================================

    @api.model
    def _moderate_comment(self, blog, comment_text):
        """
        Returns:

            {
                "blocked": True/False,
                "reason": "..."
            }
        """

        text = self._normalize_moderation_text(
            comment_text
        )

        if not text:
            return {
                "blocked": False,
                "reason": "",
            }

        # =====================================================
        # 1. HARMFUL CONTENT
        # =====================================================

        found, keyword = self._contains_keyword(
            text,
            self.HARMFUL_KEYWORDS
        )

        if found:
            return {
                "blocked": True,
                "reason": (
                    "Harmful or unsafe content "
                    "detected: %s" % keyword
                ),
            }

        # =====================================================
        # 2. SUSPICIOUS / SPAM CONTENT
        # =====================================================

        found, keyword = self._contains_keyword(
            text,
            self.SUSPICIOUS_KEYWORDS
        )

        if found:
            return {
                "blocked": True,
                "reason": (
                    "Suspicious or spam content "
                    "detected: %s" % keyword
                ),
            }

        # =====================================================
        # 3. SUSPICIOUS LINKS
        # =====================================================

        suspicious, reason = (
            self._check_suspicious_links(text)
        )

        if suspicious:
            return {
                "blocked": True,
                "reason": reason,
            }

        # =====================================================
        # 4. SPAM PATTERN
        # =====================================================

        spam, reason = self._check_spam_pattern(
            text
        )

        if spam:
            return {
                "blocked": True,
                "reason": reason,
            }

        # =====================================================
        # 5. UNRELATED CONTENT
        # =====================================================

        unrelated, reason = (
            self._check_unrelated_comment(
                blog,
                text
            )
        )

        if unrelated:
            return {
                "blocked": True,
                "reason": reason,
            }

        # =====================================================
        # APPROVED
        # =====================================================

        return {
            "blocked": False,
            "reason": "",
        }

    # =========================================================
    # CREATE COMMENT
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            blog = False

            if vals.get("blog_id"):
                blog = self.env[
                    "qevrixa.blog"
                ].sudo().browse(
                    vals["blog_id"]
                )

            comment_text = (
                vals.get("comment")
                or ""
            ).strip()

            moderation = self._moderate_comment(
                blog,
                comment_text
            )

            if moderation["blocked"]:

                vals["blocked"] = True

                vals["moderation_status"] = (
                    "blocked"
                )

                vals["block_reason"] = (
                    moderation["reason"]
                )

                # Mark as reported for admin visibility
                if "reported" in self._fields:
                    vals["reported"] = True

            else:

                vals["blocked"] = False

                vals["moderation_status"] = (
                    "approved"
                )

                vals["block_reason"] = False

        return super().create(vals_list)