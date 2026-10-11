"""DTOs de salida del foro."""

from datetime import datetime

from pydantic import BaseModel

from techzone.models import Comment, Post


class CommentOut(BaseModel):
    id: int
    author: str
    content: str
    created_at: datetime

    @classmethod
    def of(cls, comment: Comment) -> "CommentOut":
        return cls(
            id=comment.id,
            author=comment.user.name,
            content=comment.content,
            created_at=comment.created_at,
        )


EXCERPT_LENGTH = 150


def excerpt_of(content: str) -> str:
    if len(content) <= EXCERPT_LENGTH:
        return content
    return content[:EXCERPT_LENGTH] + "..."


class PostOut(BaseModel):
    id: int
    title: str
    excerpt: str
    author: str
    created_at: datetime
    views: int
    comment_count: int
    like_count: int

    @classmethod
    def of(cls, post: Post) -> "PostOut":
        return cls(
            id=post.id,
            title=post.title,
            excerpt=excerpt_of(post.content),
            author=post.user.name,
            created_at=post.created_at,
            views=post.views,
            comment_count=post.comment_count,
            like_count=post.like_count,
        )


class PostDetailOut(PostOut):
    content: str
    comments: list[CommentOut]
    # Depende de quién mira: si ya dio like, el corazón va marcado.
    liked: bool = False

    @classmethod
    def of(cls, post: Post, liked: bool = False) -> "PostDetailOut":
        return cls(
            **PostOut.of(post).model_dump(),
            content=post.content,
            comments=[CommentOut.of(c) for c in post.comments],
            liked=liked,
        )


class CommunityStatsOut(BaseModel):
    users: int
    posts: int
    comments: int
    requests: int
