"""Quick import test for tasks router and main app"""
import sys

def main():
    try:
        import app.tasks_router  # noqa: F401
        import app.main  # noqa: F401
        print("IMPORT_OK")
    except Exception as e:
        print("IMPORT_ERROR", e)
        raise

if __name__ == '__main__':
    main()
