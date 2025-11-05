from typing import List, Dict, Any, Optional
from loguru import logger


class TaskLogic:
    """Logika modułu zadań - warstwa pośrednia między UI a bazą danych.

    Metody:
    - load_tasks(): zwraca listę zadań z bazy danych
    - add_task(task): dodaje zadanie do bazy danych
    - filter_tasks(...): zwraca filtrowaną listę zadań
    """

    def __init__(self, db: Optional[Any] = None):
        self.db = db
        logger.info(f"[TaskLogic] Initialized with database: {db is not None}")

    def load_tasks(self, limit: Optional[int] = None, include_archived: bool = False) -> List[Dict[str, Any]]:
        """
        Wczytaj zadania z bazy danych
        
        Args:
            limit: Maksymalna liczba zadań (opcjonalne)
            include_archived: Czy uwzględnić zadania zarchiwizowane
            
        Returns:
            Lista słowników z zadaniami
        """
        if not self.db:
            logger.warning("[TaskLogic] No database available, returning empty list")
            return []
        
        try:
            # Pobierz zadania z bazy danych
            tasks = self.db.get_tasks(
                parent_id=None,  # Tylko główne zadania (bez podzadań)
                include_archived=include_archived,
                include_subtasks=False
            )
            
            # Rozbuduj dane o custom_data jako płaską strukturę
            enriched_tasks = []
            for task in tasks:
                # Skopiuj podstawowe pola
                enriched = dict(task)
                
                # Wyciągnij custom_data na górny poziom (jeśli istnieje)
                if 'custom_data' in task and isinstance(task['custom_data'], dict):
                    for key, value in task['custom_data'].items():
                        enriched[key] = value
                
                # Konwertuj tagi na string (dla kompatybilności)
                if 'tags' in task and isinstance(task['tags'], list):
                    enriched['tags_list'] = task['tags']
                    enriched['tags'] = ', '.join([tag.get('name', '') for tag in task['tags']])
                
                enriched_tasks.append(enriched)
            
            # Ogranicz liczbę wyników jeśli podano limit
            if limit:
                enriched_tasks = enriched_tasks[:limit]
            
            logger.info(f"[TaskLogic] Loaded {len(enriched_tasks)} tasks from database")
            return enriched_tasks
            
        except Exception as e:
            logger.error(f"[TaskLogic] Failed to load tasks: {e}")
            return []

    def add_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Dodaj nowe zadanie do bazy danych
        
        Args:
            task: Słownik z danymi zadania
            
        Returns:
            Dodane zadanie lub None w przypadku błędu
        """
        if not self.db:
            logger.warning("[TaskLogic] No database available, cannot add task")
            return None
        
        try:
            title = task.get('title', 'Nowe zadanie')
            parent_id = task.get('parent_id')

            custom_data: Dict[str, Any] = {}
            if isinstance(task.get('custom_data'), dict):
                custom_data.update(task['custom_data'])

            direct_keys = {
                'status',
                'completion_date',
                'kanban_id',
                'note_id',
                'alarm_date',
                'row_color',
            }

            extra_kwargs: Dict[str, Any] = {}
            for key in direct_keys:
                if key in task and task[key] is not None:
                    extra_kwargs[key] = task[key]

            tags = None
            if isinstance(task.get('tags'), list):
                tags = [tag for tag in task['tags'] if tag is not None]

            for key, value in task.items():
                if key in {'title', 'parent_id', 'custom_data', 'tags', 'add_to_kanban'}:
                    continue
                if key in direct_keys:
                    continue
                if value is not None:
                    custom_data[key] = value

            task_id = self.db.add_task(
                title=title,
                parent_id=parent_id,
                custom_data=custom_data or None,
                tags=tags,
                **extra_kwargs,
            )
            
            if task_id:
                logger.info(f"[TaskLogic] Added task with ID {task_id}")
                # Pobierz świeżo dodane zadanie z bazy
                tasks = self.db.get_tasks(parent_id=None, include_archived=False, include_subtasks=False)
                for t in tasks:
                    if t.get('id') == task_id:
                        return t
            
            return None
            
        except Exception as e:
            logger.error(f"[TaskLogic] Failed to add task: {e}")
            return None

    def filter_tasks(self, text: str = '', status: Optional[str] = 'all', tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Filtruj zadania na podstawie tekstu, statusu i tagu
        
        Args:
            text: Tekst do wyszukania
            status: Klucz filtra statusu ('all', 'active', 'completed', 'archived') lub ekwiwalentny opis
            tag: Nazwa tagu do filtrowania (None/'Wszystkie' = bez filtra)
            
        Returns:
            Przefiltrowana lista zadań
        """
        status_key = (status or 'all')
        if isinstance(status_key, str):
            normalized = status_key.lower()
            status_map = {
                'wszystkie': 'all',
                'all': 'all',
                'aktywne': 'active',
                'active': 'active',
                'ukończone': 'completed',
                'ukonczone': 'completed',
                'completed': 'completed',
                'zarchiwizowane': 'archived',
                'zarchwizowane': 'archived',
                'archived': 'archived',
            }
            status_key = status_map.get(normalized, 'all')
        else:
            status_key = 'all'

        include_archived = status_key == 'archived'

        # Pobierz wszystkie zadania zgodnie z wybranym statusem
        all_tasks = self.load_tasks(include_archived=include_archived)

        text_query = (text or '').lower().strip()
        tag_query = (tag or '').strip()
        tag_query_lower = tag_query.lower()
        if tag_query_lower in {'', 'wszystkie', 'all'}:
            tag_query_lower = ''

        filtered: List[Dict[str, Any]] = []

        for task in all_tasks:
            is_completed = bool(task.get('status'))
            is_archived = bool(task.get('archived'))

            if status_key == 'active':
                if is_archived or is_completed:
                    continue
            elif status_key == 'completed':
                if is_archived or not is_completed:
                    continue
            elif status_key == 'archived':
                if not is_archived:
                    continue
            else:  # 'all'
                if is_archived:
                    continue

            if tag_query_lower:
                tags_match = False
                tags_list = task.get('tags_list')
                if isinstance(tags_list, list):
                    tags_match = any(
                        isinstance(t, dict) and (t.get('name', '').lower() == tag_query_lower)
                        for t in tags_list
                    )
                if not tags_match:
                    tags_str = task.get('tags', '')
                    if isinstance(tags_str, str):
                        tags_match = tag_query_lower in tags_str.lower()
                if not tags_match:
                    continue

            if text_query:
                title = task.get('title', '') or ''
                tags_text = task.get('tags', '') or ''
                searchable = f"{title} {tags_text}".lower()
                if text_query not in searchable:
                    continue

            filtered.append(task)

        logger.info(f"[TaskLogic] Filtered {len(filtered)} tasks from {len(all_tasks)}")
        return filtered
