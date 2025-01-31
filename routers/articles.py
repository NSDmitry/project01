from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database import get_db
from models.Article import Article
from common.ArticleSchema import ArticleSchema

router = APIRouter(prefix="/api/articles", tags=["articles"])

@router.post("/", response_model=ArticleSchema)
def create_article(article: ArticleSchema, db: Session = Depends(get_db)):
    article = Article(**article.dict())
    db.add(article)
    db.commit()
    db.refresh(article)
    return article

@router.get("/")
def get_articles(db: Session = Depends(get_db)):
    return db.query(Article).all()

@router.get("/{article_id}")
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@router.delete("/{article_id}")
def delete_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"message": "Article deleted successfully"}
