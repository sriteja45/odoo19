# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from werkzeug.utils import redirect
import math
import re
import os
import requests
from datetime import datetime, timedelta


class QevrixaBlogController(http.Controller):

    # ============================================================
    # BLOG LISTING
    # ============================================================

    @http.route(
        '/blog',
        type='http',
        auth='public',
        website=True,
        sitemap=True
    )
    def blog_list(
        self,
        category_id=None,
        author_id=None,
        publish_date=None,
        search=None,
        sort=None,
        page=1,
        **kwargs
    ):

        Blog = request.env['qevrixa.blog'].sudo()

        domain = [
            ('published', '=', True)
        ]

        # --------------------------------------------------------
        # CATEGORY FILTER
        # --------------------------------------------------------

        if category_id:
            try:
                category_id = int(category_id)

                domain.append(
                    ('category_id', '=', category_id)
                )

            except (ValueError, TypeError):
                category_id = None

        # --------------------------------------------------------
        # AUTHOR FILTER
        # --------------------------------------------------------

        if author_id:
            try:
                author_id = int(author_id)

                domain.append(
                    ('author_id', '=', author_id)
                )

            except (ValueError, TypeError):
                author_id = None

        # --------------------------------------------------------
        # DATE FILTER
        # --------------------------------------------------------
        # Search from selected date until the next day.

        if publish_date:

            try:

                selected_date = datetime.strptime(
                    publish_date,
                    '%Y-%m-%d'
                )

                next_date = (
                    selected_date +
                    timedelta(days=1)
                )

                domain.append(
                    (
                        'publish_date',
                        '>=',
                        selected_date.strftime(
                            '%Y-%m-%d 00:00:00'
                        )
                    )
                )

                domain.append(
                    (
                        'publish_date',
                        '<',
                        next_date.strftime(
                            '%Y-%m-%d 00:00:00'
                        )
                    )
                )

            except (ValueError, TypeError):

                publish_date = None

        # --------------------------------------------------------
        # SEARCH
        # --------------------------------------------------------

        if search:

            search = search.strip()

            if search:

                domain += [
                    '|',
                    '|',
                    ('name', 'ilike', search),
                    ('content', 'ilike', search),
                    ('description', 'ilike', search),
                ]

        # --------------------------------------------------------
        # SORTING
        # --------------------------------------------------------

        order = 'publish_date desc, id desc'

        if sort == 'name':

            order = 'name asc'

        elif sort == 'name_desc':

            order = 'name desc'

        elif sort == 'oldest':

            order = 'publish_date asc, id asc'

        elif sort == 'views':

            if 'views' in Blog._fields:
                order = 'views desc, id desc'

        elif sort == 'likes':

            if 'likes' in Blog._fields:
                order = 'likes desc, id desc'

        # --------------------------------------------------------
        # PAGINATION
        # --------------------------------------------------------

        blogs_per_page = 6

        try:

            page = int(page)

        except (ValueError, TypeError):

            page = 1

        if page < 1:
            page = 1

        total_blogs = Blog.search_count(domain)

        total_pages = (
            math.ceil(
                total_blogs /
                blogs_per_page
            )
            if total_blogs
            else 1
        )

        if page > total_pages:
            page = total_pages

        offset = (
            (page - 1) *
            blogs_per_page
        )

        blogs = Blog.search(
            domain,
            order=order,
            limit=blogs_per_page,
            offset=offset
        )

        # ========================================================
        # CATEGORIES
        # ========================================================
        #
        # IMPORTANT:
        #
        # Do NOT directly use:
        #
        # request.env['qevrixa.blog.category']
        #
        # because that model may not be registered.
        #
        # Instead, get the actual model used by category_id.
        #
        # ========================================================

        categories = request.env['qevrixa.blog'].browse()

        category_field = Blog._fields.get('category_id')

        if category_field and getattr(
            category_field,
            'comodel_name',
            False
        ):

            category_model_name = (
                category_field.comodel_name
            )

            category_model = request.env.registry.models.get(
                category_model_name
            )

            if category_model:

                categories = request.env[
                    category_model_name
                ].sudo().search([])

        # --------------------------------------------------------
        # AUTHORS
        # --------------------------------------------------------

        authors = request.env[
            'res.users'
        ].sudo().search([
            ('share', '=', False)
        ])

        # --------------------------------------------------------
        # VALUES
        # --------------------------------------------------------

        values = {

            'blogs': blogs,

            'categories': categories,

            'authors': authors,

            'search': search or '',

            'selected_category_id':
                category_id,

            'selected_author_id':
                author_id,

            'selected_publish_date':
                publish_date,

            'selected_sort':
                sort or '',

            'page': page,

            'total_pages':
                total_pages,

            'total_blogs':
                total_blogs,
        }

        return request.render(
            'qevrixa_blog.blog_list_template',
            values
        )


    # ============================================================
    # BLOG DETAIL
    # ============================================================

    @http.route(
        '/blog/<string:slug>',
        type='http',
        auth='public',
        website=True,
        sitemap=True
    )
    def blog_detail(self, slug, **kwargs):

        Blog = request.env['qevrixa.blog'].sudo()

        # --------------------------------------------------------
        # FIND BLOG
        # --------------------------------------------------------

        blog = Blog.search([
            ('slug', '=', slug),
            ('published', '=', True)
        ], limit=1)

        if not blog:

            return request.not_found()

        # --------------------------------------------------------
        # INCREASE VIEW COUNT
        # --------------------------------------------------------

        if 'views' in blog._fields:

            blog.write({
                'views': (
                    blog.views or 0
                ) + 1
            })

        # --------------------------------------------------------
        # BLOG CONTENT
        # --------------------------------------------------------

        content = blog.content or ''

        # --------------------------------------------------------
        # REMOVE HTML TAGS
        # --------------------------------------------------------

        plain_text = re.sub(
            r'<[^>]+>',
            ' ',
            content
        )

        # --------------------------------------------------------
        # REMOVE EXTRA SPACES
        # --------------------------------------------------------

        plain_text = re.sub(
            r'\s+',
            ' ',
            plain_text
        ).strip()

        # --------------------------------------------------------
        # WORD COUNT
        # --------------------------------------------------------

        words = plain_text.split()

        word_count = len(words)

        # --------------------------------------------------------
        # READING TIME
        # Average = 200 words / minute
        # --------------------------------------------------------

        reading_time = max(
            1,
            math.ceil(
                word_count / 200
            )
        )

        # --------------------------------------------------------
        # LIKES
        # --------------------------------------------------------

        likes = 0

        if 'likes' in blog._fields:

            likes = blog.likes or 0

        # --------------------------------------------------------
        # DISLIKES
        # --------------------------------------------------------

        dislikes = 0

        if 'dislikes' in blog._fields:

            dislikes = blog.dislikes or 0

        # --------------------------------------------------------
        # RELATED BLOGS
        # --------------------------------------------------------

        related_blogs = Blog.browse()

        if blog.category_id:

            related_blogs = Blog.search([
                ('id', '!=', blog.id),
                ('published', '=', True),
                (
                    'category_id',
                    '=',
                    blog.category_id.id
                ),
            ],
                order='publish_date desc, id desc',
                limit=5
            )

        # --------------------------------------------------------
        # FALLBACK RELATED BLOGS
        # --------------------------------------------------------

        if not related_blogs:

            related_blogs = Blog.search([
                ('id', '!=', blog.id),
                ('published', '=', True),
            ],
                order='publish_date desc, id desc',
                limit=5
            )

        # ========================================================
        # PREVIOUS BLOG
        # ========================================================
        #
        # BLOG LIST ORDER:
        #
        # 1. Newest blog
        # 2. Second newest blog
        # 3. Third newest blog
        # 4. ...
        #
        # Therefore:
        #
        # Previous = newer blog
        #
        # Example:
        #
        # Blog 2 -> Previous = Blog 1
        # Blog 3 -> Previous = Blog 2
        #
        # ========================================================

        previous_blog = Blog.browse()

        if blog.publish_date:

            previous_blog = Blog.search([
                ('published', '=', True),
                '|',
                (
                    'publish_date',
                    '>',
                    blog.publish_date
                ),
                '&',
                (
                    'publish_date',
                    '=',
                    blog.publish_date
                ),
                (
                    'id',
                    '>',
                    blog.id
                ),
            ],
                order='publish_date asc, id asc',
                limit=1
            )

        # ========================================================
        # NEXT BLOG
        # ========================================================
        #
        # Since the listing is:
        #
        # newest -> oldest
        #
        # Next = older blog
        #
        # Example:
        #
        # Blog 1 -> Next = Blog 2
        # Blog 2 -> Next = Blog 3
        # Blog 3 -> Next = Blog 4
        #
        # ========================================================

        next_blog = Blog.browse()

        if blog.publish_date:

            next_blog = Blog.search([
                ('published', '=', True),
                '|',
                (
                    'publish_date',
                    '<',
                    blog.publish_date
                ),
                '&',
                (
                    'publish_date',
                    '=',
                    blog.publish_date
                ),
                (
                    'id',
                    '<',
                    blog.id
                ),
            ],
                order='publish_date desc, id desc',
                limit=1
            )

        # ========================================================
        # COMMENTS
        # ========================================================

        Comment = request.env[
            'qevrixa.blog.comment'
        ].sudo()

        comment_domain = [
            ('blog_id', '=', blog.id)
        ]

        # --------------------------------------------------------
        # BLOCKED COMMENTS SHOULD NOT DISPLAY
        # --------------------------------------------------------

        if 'blocked' in Comment._fields:

            comment_domain.append(
                ('blocked', '=', False)
            )

        comments = Comment.search(
            comment_domain,
            order='create_date desc'
        )

        comments_count = len(comments)

        # --------------------------------------------------------
        # SHOW COMMENTS ONLY FOR LOGGED-IN USERS
        # --------------------------------------------------------

        public_user = request.env.ref(
            'base.public_user'
        )

        show_comments = (
            request.env.user.id !=
            public_user.id
        )

        # ========================================================
        # VALUES TO TEMPLATE
        # ========================================================

        values = {

            'blog': blog,

            'related_blogs':
                related_blogs,

            'previous_blog':
                previous_blog,

            'next_blog':
                next_blog,

            'comments':
                comments,

            'comments_count':
                comments_count,

            'show_comments':
                show_comments,

            'reading_time':
                reading_time,

            'word_count':
                word_count,

            'likes':
                likes,

            'dislikes':
                dislikes,
        }

        return request.render(
            'qevrixa_blog.blog_detail_template',
            values
        )


    # ============================================================
    # LIKE BLOG
    # ============================================================

    @http.route(
        '/blog/like/<int:blog_id>',
        type='http',
        auth='public',
        website=True
    )
    def like_blog(self, blog_id, **kwargs):

        blog = request.env[
            'qevrixa.blog'
        ].sudo().browse(blog_id)

        if not blog.exists():

            return request.not_found()

        if 'likes' in blog._fields:

            blog.write({
                'likes': (
                    blog.likes or 0
                ) + 1
            })

        return redirect(
            '/blog/%s' % blog.slug
        )


    # ============================================================
    # DISLIKE BLOG
    # ============================================================

    @http.route(
        '/blog/dislike/<int:blog_id>',
        type='http',
        auth='public',
        website=True
    )
    def dislike_blog(self, blog_id, **kwargs):

        blog = request.env[
            'qevrixa.blog'
        ].sudo().browse(blog_id)

        if not blog.exists():

            return request.not_found()

        if 'dislikes' in blog._fields:

            blog.write({
                'dislikes': (
                    blog.dislikes or 0
                ) + 1
            })

        return redirect(
            '/blog/%s' % blog.slug
        )


    # ============================================================
    # REPORT BLOG
    # ============================================================

    @http.route(
        '/blog/report/<int:blog_id>',
        type='http',
        auth='user',
        website=True,
        methods=['POST']
    )
    def report_blog(self, blog_id, **kwargs):

        blog = request.env[
            'qevrixa.blog'
        ].sudo().browse(blog_id)

        if not blog.exists():

            return request.not_found()

        vals = {}

        # --------------------------------------------------------
        # REPORTED
        # --------------------------------------------------------

        if 'reported' in blog._fields:

            vals['reported'] = True

        # --------------------------------------------------------
        # REPORT COUNT
        # --------------------------------------------------------

        if 'report_count' in blog._fields:

            vals['report_count'] = (
                blog.report_count or 0
            ) + 1

        # --------------------------------------------------------
        # WRITE
        # --------------------------------------------------------

        if vals:

            blog.write(vals)

        return redirect(
            '/blog/%s' % blog.slug
        )


    # ============================================================
    # ADD COMMENT
    # ============================================================

    @http.route(
        '/blog/comment/<int:blog_id>',
        type='http',
        auth='user',
        website=True,
        methods=['POST']
    )
    def add_comment(self, blog_id, **kwargs):

        Blog = request.env[
            'qevrixa.blog'
        ].sudo()

        Comment = request.env[
            'qevrixa.blog.comment'
        ].sudo()

        # --------------------------------------------------------
        # FIND BLOG
        # --------------------------------------------------------

        blog = Blog.browse(blog_id)

        if not blog.exists():

            return request.not_found()

        # --------------------------------------------------------
        # COMMENT TEXT
        # --------------------------------------------------------

        comment_text = (
            kwargs.get('comment') or ''
        ).strip()

        if not comment_text:

            return redirect(
                '/blog/%s' % blog.slug
            )

        # --------------------------------------------------------
        # CURRENT USER
        # --------------------------------------------------------

        user = request.env.user

        # --------------------------------------------------------
        # COMMENT VALUES
        # --------------------------------------------------------

        vals = {

            'blog_id':
                blog.id,

            'name':
                user.name,

            'email':
                user.email or '',

            'comment':
                comment_text,
        }

        # --------------------------------------------------------
        # OPTIONAL USER ID
        # --------------------------------------------------------

        if 'user_id' in Comment._fields:

            vals['user_id'] = user.id

        # --------------------------------------------------------
        # BLOCKED
        # --------------------------------------------------------

        if 'blocked' in Comment._fields:

            vals['blocked'] = False

        # --------------------------------------------------------
        # LIKES
        # --------------------------------------------------------

        if 'likes' in Comment._fields:

            vals['likes'] = 0

        # --------------------------------------------------------
        # DISLIKES
        # --------------------------------------------------------

        if 'dislikes' in Comment._fields:

            vals['dislikes'] = 0

        # --------------------------------------------------------
        # REPORT COUNT
        # --------------------------------------------------------

        if 'report_count' in Comment._fields:

            vals['report_count'] = 0

        # --------------------------------------------------------
        # REPORTED
        # --------------------------------------------------------

        if 'reported' in Comment._fields:

            vals['reported'] = False

        # --------------------------------------------------------
        # CREATE COMMENT
        # --------------------------------------------------------

        Comment.create(vals)

        return redirect(
            '/blog/%s' % blog.slug
        )


    # ============================================================
    # LIKE COMMENT
    # ============================================================

    @http.route(
        '/blog/comment/like/<int:comment_id>',
        type='http',
        auth='user',
        website=True,
        methods=['POST']
    )
    def like_comment(
        self,
        comment_id,
        **kwargs
    ):

        Comment = request.env[
            'qevrixa.blog.comment'
        ].sudo()

        comment = Comment.browse(
            comment_id
        )

        if not comment.exists():

            return request.not_found()

        # --------------------------------------------------------
        # LIKE
        # --------------------------------------------------------

        if 'likes' in comment._fields:

            comment.write({
                'likes': (
                    comment.likes or 0
                ) + 1
            })

        # --------------------------------------------------------
        # REDIRECT
        # --------------------------------------------------------

        if comment.blog_id:

            return redirect(
                '/blog/%s' %
                comment.blog_id.slug
            )

        return redirect('/blog')


    # ============================================================
    # DISLIKE COMMENT
    # ============================================================

    @http.route(
        '/blog/comment/dislike/<int:comment_id>',
        type='http',
        auth='user',
        website=True,
        methods=['POST']
    )
    def dislike_comment(
        self,
        comment_id,
        **kwargs
    ):

        Comment = request.env[
            'qevrixa.blog.comment'
        ].sudo()

        comment = Comment.browse(
            comment_id
        )

        if not comment.exists():

            return request.not_found()

        # --------------------------------------------------------
        # DISLIKE
        # --------------------------------------------------------

        if 'dislikes' in comment._fields:

            comment.write({
                'dislikes': (
                    comment.dislikes or 0
                ) + 1
            })

        # --------------------------------------------------------
        # REDIRECT
        # --------------------------------------------------------

        if comment.blog_id:

            return redirect(
                '/blog/%s' %
                comment.blog_id.slug
            )

        return redirect('/blog')


    # ============================================================
    # REPORT COMMENT
    # ============================================================

    @http.route(
        '/blog/comment/report/<int:comment_id>',
        type='http',
        auth='user',
        website=True,
        methods=['POST']
    )
    def report_comment(
        self,
        comment_id,
        **kwargs
    ):

        Comment = request.env[
            'qevrixa.blog.comment'
        ].sudo()

        comment = Comment.browse(
            comment_id
        )

        if not comment.exists():

            return request.not_found()

        vals = {}

        # --------------------------------------------------------
        # REPORTED
        # --------------------------------------------------------

        if 'reported' in comment._fields:

            vals['reported'] = True

        # --------------------------------------------------------
        # REPORT COUNT
        # --------------------------------------------------------

        if 'report_count' in comment._fields:

            vals['report_count'] = (
                comment.report_count or 0
            ) + 1

        # --------------------------------------------------------
        # REPORT REASON
        # --------------------------------------------------------

        if 'report_reason' in comment._fields:

            vals['report_reason'] = (
                kwargs.get('report_reason')
                or
                'Reported by user'
            )

        # --------------------------------------------------------
        # WRITE
        # --------------------------------------------------------

        if vals:

            comment.write(vals)

        # --------------------------------------------------------
        # REDIRECT
        # --------------------------------------------------------

        if comment.blog_id:

            return redirect(
                '/blog/%s' %
                comment.blog_id.slug
            )

        return redirect('/blog')


    # ============================================================
    # BLOG CHAT
    # ============================================================

    @http.route(
        '/blog/chat',
        type='json',
        auth='public',
        website=True
    )
    def blog_chat(
        self,
        message=None,
        **kwargs
    ):

        # --------------------------------------------------------
        # VALIDATE MESSAGE
        # --------------------------------------------------------

        if not message:

            return {
                'success': False,
                'message':
                    'Please enter a message.'
            }

        # --------------------------------------------------------
        # FASTAPI CHAT URL
        # --------------------------------------------------------

        chat_url = os.environ.get(
            'FASTAPI_CHAT_URL',
            'http://127.0.0.1:8000/agent/chat'
        )

        # --------------------------------------------------------
        # TIMEOUT
        # --------------------------------------------------------

        try:

            timeout = int(
                os.environ.get(
                    'FASTAPI_TIMEOUT',
                    '30'
                )
            )

        except (
            ValueError,
            TypeError
        ):

            timeout = 30

        # --------------------------------------------------------
        # REQUEST FASTAPI
        # --------------------------------------------------------

        try:

            response = requests.post(

                chat_url,

                json={
                    'message': message
                },

                timeout=timeout
            )

            response.raise_for_status()

            data = response.json()

            # ----------------------------------------------------
            # RESPONSE
            # ----------------------------------------------------

            return {

                'success': True,

                'response':
                    data.get(
                        'response',
                        data.get(
                            'message',
                            ''
                        )
                    )
            }

        # --------------------------------------------------------
        # REQUEST ERROR
        # --------------------------------------------------------

        except requests.exceptions.RequestException as error:

            return {

                'success': False,

                'message':
                    str(error)
            }

        # --------------------------------------------------------
        # GENERAL ERROR
        # --------------------------------------------------------

        except Exception as error:

            return {

                'success': False,

                'message':
                    str(error)
            }