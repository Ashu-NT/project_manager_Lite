from sqlalchemy.orm import Session

class ServiceBase:
    def __init__(self, session: Session):
        self._session = session
    
    def commit(self):
        try:
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e

