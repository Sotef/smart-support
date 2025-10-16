"""
Сервис категоризации запросов на основе сравнения эмбеддингов с вопросами из базы знаний
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class KnowledgeBaseCategorizer:
    """Категоризатор на основе эмбеддингов вопросов из базы знаний"""
    
    def __init__(self, knowledge_base=None, scibox_service=None):
        self.knowledge_base = knowledge_base
        self.scibox_service = scibox_service
        self.kb_embeddings = {}
        self.articles_cache = []
        self.initialized = False
    
    async def initialize_from_knowledge_base(self):
        """Инициализация категоризатора с эмбеддингами из БЗ"""
        if not self.knowledge_base or not self.scibox_service:
            logger.error("Knowledge base or Scibox service not provided")
            return False
            
        try:
            # Кешируем статьи из БЗ
            self.articles_cache = self.knowledge_base.articles
            
            if not self.articles_cache:
                logger.warning("No articles found in knowledge base")
                return False
            
            # Генерируем эмбеддинги для всех вопросов (title) из БЗ
            titles = [article.title for article in self.articles_cache]
            
            logger.info(f"Generating embeddings for {len(titles)} KB questions...")
            embeddings = await self.scibox_service.embed_texts(titles)
            
            # Сохраняем эмбеддинги с соответствующими статьями
            self.kb_embeddings = {
                self.articles_cache[i].id: embeddings[i] 
                for i in range(len(self.articles_cache))
            }
            
            self.initialized = True
            logger.info(f"Successfully initialized KB categorizer with {len(self.kb_embeddings)} embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize KB categorizer: {e}")
            return False

    async def categorize_text(self, text: str) -> Tuple[str, str, float]:
        """
        Категоризация текста через сравнение эмбеддингов с вопросами из БЗ
        
        Returns:
            Tuple[category, subcategory, confidence]
        """
        try:
            if not self.initialized or not self.kb_embeddings or not self.scibox_service:
                logger.warning("KB Categorizer not initialized, returning default")
                return "общие вопросы", "консультация", 0.3
            
            # Получаем эмбеддинг входящего вопроса
            query_embeddings = await self.scibox_service.embed_texts([text])
            query_embedding = query_embeddings[0]
            
            # Сравниваем с всеми эмбеддингами вопросов из БЗ
            best_similarity = 0.0
            best_article = None
            
            for article in self.articles_cache:
                if article.id in self.kb_embeddings:
                    kb_embedding = self.kb_embeddings[article.id]
                    
                    # Проверяем совместимость размерностей
                    if len(query_embedding) != len(kb_embedding):
                        logger.warning(f"Dimension mismatch: query={len(query_embedding)}, kb={len(kb_embedding)}, skipping article {article.id}")
                        continue
                    
                    # Вычисляем cosine similarity
                    try:
                        similarity = cosine_similarity(
                            [query_embedding], [kb_embedding]
                        )[0][0]
                    except ValueError as e:
                        logger.warning(f"Cosine similarity failed for article {article.id}: {e}")
                        continue
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_article = article
            
            if best_article and best_similarity > 0.25:  # Минимальный порог сходства
                # Берем категорию и подкатегорию из найденной статьи БЗ
                category = best_article.main_category or best_article.category.value or "общие вопросы"
                subcategory = best_article.subcategory or "консультация"
                confidence = min(best_similarity, 0.95)  # Максимальная уверенность 95%
                
                logger.debug(f"Found best KB match: '{best_article.title}' (similarity: {best_similarity:.3f})")
                logger.debug(f"Category: '{category}', Subcategory: '{subcategory}'")
                
                return category, subcategory, confidence
            else:
                logger.debug(f"No good KB match found, best similarity: {best_similarity:.3f}")
                return "общие вопросы", "консультация", 0.3
                
        except Exception as e:
            logger.error(f"Error in KB embedding categorization: {e}")
            return "общие вопросы", "консультация", 0.3

    def get_category_display_name(self, category: str) -> str:
        """Получить отображаемое имя категории"""
        return category  # Возвращаем категорию как есть из БЗ

    def get_subcategory_display_name(self, category: str, subcategory: str) -> str:
        """Получить отображаемое имя подкатегории"""
        return subcategory  # Возвращаем подкатегорию как есть из БЗ
    
    def get_stats(self) -> Dict:
        """Получить статистику категоризатора"""
        categories = {}
        subcategories = {}
        
        for article in self.articles_cache:
            cat = article.main_category or article.category.value or "общие"
            subcat = article.subcategory or "другое"
            
            categories[cat] = categories.get(cat, 0) + 1
            
            if cat not in subcategories:
                subcategories[cat] = {}
            subcategories[cat][subcat] = subcategories[cat].get(subcat, 0) + 1
        
        return {
            "initialized": self.initialized,
            "total_articles": len(self.articles_cache),
            "total_embeddings": len(self.kb_embeddings),
            "categories": categories,
            "subcategories": subcategories
        }