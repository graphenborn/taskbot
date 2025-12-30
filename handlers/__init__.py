"""Пакет с обработчиками команд бота"""
from handlers.main import router
from handlers.admin import admin_router

__all__ = ['router', 'admin_router']
