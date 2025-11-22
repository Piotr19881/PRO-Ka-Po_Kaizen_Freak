"""Sample data set used by the TeamWork module during prototyping."""

from __future__ import annotations

from datetime import datetime

SAMPLE_GROUPS = [
    {
        "id": "grp-marketing",
        "name": "Marketing 2025",
        "description": "Planowanie kampanii i materiały kreatywne.",
        "members": ["Anna", "Bartek", "Celina", "Damian"],
        "topics": [
            {
                "id": "top-launch",
                "title": "Kampania wiosenna",
                "created_at": datetime(2025, 2, 15, 9, 0),
                "owner": "Anna",
                "plans": [
                    "Zbierz brief produktowy",
                    "Przygotuj harmonogram publikacji",
                    "Koordynuj dostawców materiałów wideo",
                ],
                "messages": [
                    {
                        "id": "msg-001",
                        "author": "Anna",
                        "posted_at": datetime(2025, 3, 1, 10, 45),
                        "content": "Proszę o potwierdzenie zakresu budżetu do końca tygodnia.",
                        "important": True,
                        "background_color": "#E3F2FD",
                        "files": [],
                        "links": [
                            {
                                "id": "link-001",
                                "url": "https://example.com/brief",
                                "title": "Brief kampanii",
                                "author": "Anna",
                                "added_at": datetime(2025, 3, 1, 10, 50),
                                "important": False,
                            }
                        ],
                    },
                    {
                        "id": "msg-002",
                        "author": "Bartek",
                        "posted_at": datetime(2025, 3, 2, 14, 5),
                        "content": "Załączam draft harmonogramu do przeglądu.",
                        "important": False,
                        "background_color": "#E8F5E9",
                        "files": [
                            {
                                "id": "file-001",
                                "path": "harmonogram_v1.xlsx",
                                "author": "Bartek",
                                "added_at": datetime(2025, 3, 2, 14, 6),
                                "note": "Draft do uwag",
                                "important": False,
                            }
                        ],
                        "links": [],
                    },
                ],
                "files": [
                    {
                        "id": "file-002",
                        "path": "brief_marketing.pdf",
                        "author": "Anna",
                        "added_at": datetime(2025, 2, 15, 10, 10),
                        "note": "Wersja zaakceptowana przez zarząd",
                        "important": True,
                    },
                    {
                        "id": "file-003",
                        "path": "harmonogram_v1.xlsx",
                        "author": "Bartek",
                        "added_at": datetime(2025, 3, 2, 14, 6),
                        "note": "Szkic do omówienia",
                        "important": False,
                    },
                ],
                "links": [
                    {
                        "id": "link-002",
                        "url": "https://figma.com/file/mock",
                        "title": "Makiety kampanii",
                        "author": "Celina",
                        "added_at": datetime(2025, 3, 3, 9, 20),
                        "important": True,
                    }
                ],
                "tasks": [
                    {
                        "id": "task-001",
                        "title": "Przygotować brief produktowy",
                        "description": "Zebrać informacje o produkcie, grupy docelowej i budżecie.",
                        "creator": "Anna",
                        "assignee": "Bartek",
                        "deadline": datetime(2025, 3, 10, 23, 59),
                        "completed": True,
                        "created_at": datetime(2025, 3, 1, 9, 0),
                        "completed_at": datetime(2025, 3, 8, 14, 30),
                        "completed_by": "Anna",
                        "important": False,
                    },
                    {
                        "id": "task-002",
                        "title": "Zaakceptować harmonogram publikacji",
                        "description": "Przejrzeć i zatwierdzić harmonogram przygotowany przez Bartka.",
                        "creator": "Anna",
                        "assignee": "Celina",
                        "deadline": datetime(2025, 3, 15, 23, 59),
                        "completed": False,
                        "created_at": datetime(2025, 3, 2, 15, 0),
                        "completed_at": None,
                        "completed_by": "",
                        "important": True,
                    },
                ],
            },
            {
                "id": "top-content",
                "title": "Content plan social media",
                "created_at": datetime(2025, 2, 20, 11, 30),
                "owner": "Celina",
                "plans": [
                    "Przygotuj listę postów",
                    "Zgłoś potrzeby grafik",
                    "Zaplanowanie kampanii płatnych",
                ],
                "messages": [],
                "files": [],
                "links": [],
                "tasks": [],
            },
        ],
    },
    {
        "id": "grp-dev",
        "name": "Zespół developerski",
        "description": "Usprawnienia aplikacji mobilnej.",
        "members": ["Ewa", "Filip", "Grzegorz"],
        "topics": [
            {
                "id": "top-architecture",
                "title": "Architektura modułu synchronizacji",
                "created_at": datetime(2025, 1, 10, 15, 0),
                "owner": "Ewa",
                "plans": [
                    "Analiza API partnerów",
                    "Proof of Concept synchronizacji offline",
                ],
                "messages": [
                    {
                        "id": "msg-010",
                        "author": "Filip",
                        "posted_at": datetime(2025, 1, 12, 9, 15),
                        "content": "Dodaję dokument diagramów sekwencji.",
                        "files": [
                            {
                                "path": "diagramy_seq.drawio",
                                "author": "Filip",
                                "added_at": datetime(2025, 1, 12, 9, 17),
                                "note": "Wersja wstępna",
                            }
                        ],
                        "links": [],
                    }
                ],
                "files": [],
                "links": [],
                "tasks": [
                    {
                        "id": "task-dev-001",
                        "title": "Analiza API partnerów zewnętrznych",
                        "description": "Sprawdzić dokumentację API i wymagania integracji.",
                        "creator": "Ewa",
                        "assignee": "Filip",
                        "deadline": datetime(2025, 1, 20, 23, 59),
                        "completed": False,
                        "created_at": datetime(2025, 1, 10, 16, 0),
                        "completed_at": None,
                    },
                ],
            }
        ],
    },
]
