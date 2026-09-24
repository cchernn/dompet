from typing import Type, Callable

def load_db(db_model: Type):
    def load_db_func(func: Callable):
        def db_wrapper(params: Type, *args, **kwargs):
            db = db_model(params)
            result = func(params, db, *args, **kwargs)
            db.close()
            return result
        return db_wrapper
    return load_db_func