from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Blog
from app.schemas.schemas import BlogCreate, BlogUpdate
from typing import List, Dict, Any
from datetime import datetime, timezone

router = APIRouter(prefix="/blogs", tags=["Blogs"])

@router.post("/create", status_code=201)
def create_blog(
    blog_data: BlogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new blog post.
    """
    new_blog = Blog(
        user_id=current_user.user_id,
        title=blog_data.title,
        content=blog_data.content
    )
    
    db.add(new_blog)
    db.commit()
    db.refresh(new_blog)
    
    return {
        "message": "Blog created successfully",
        "blogId": new_blog.blog_id
    }

@router.get("/", status_code=200)
def get_all_blogs(db: Session = Depends(get_db)):
    """
    Returns all blog posts.
    """
    # Fetch all active blogs
    blogs = db.query(Blog).filter(Blog.is_active == True).all()
    
    response_data = []
    for blog in blogs:
        response_data.append({
            "id": blog.blog_id,
            "title": blog.title,
            "content": blog.content,
            "created_at": blog.created_at.isoformat() if blog.created_at else None,
            "author_name": blog.user.name if blog.user else "Anonymous"
        })
        
    return {"blogs": response_data}

@router.put("/{blog_id}", status_code=200)
def update_blog(
    blog_id: int,
    update_data: BlogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates an existing blog post.
    """
    blog = db.query(Blog).filter(Blog.blog_id == blog_id, Blog.is_active == True).first()
    
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
        
    if blog.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this blog")
        
    if update_data.title is not None:
        blog.title = update_data.title
    if update_data.content is not None:
        blog.content = update_data.content
        
    db.commit()
    db.refresh(blog)
    
    return {
        "message": "Blog updated successfully",
        "blog": {
            "id": blog.blog_id,
            "title": blog.title,
            "content": blog.content,
            "updated_at": blog.updated_at
        }
    }


@router.delete("/{blog_id}", status_code=200)
def delete_blog(
    blog_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft deletes a blog post.
    """
    blog = db.query(Blog).filter(Blog.blog_id == blog_id, Blog.is_active == True).first()
    
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
        
    if blog.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this blog")
        
    blog.is_active = False
    blog.deleted_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"message": "Blog deleted successfully"}
