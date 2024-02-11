import sqlite3
import os
from typing import Any, Dict, List, Optional, Literal, Tuple
from uuid import uuid4
from datetime import datetime

SCHEMA_LATEST = 1

def init_db(fpath: str, defaults: dict={}):
    now = datetime.now().isoformat()
    db = sqlite3.connect(fpath)
    cur = db.cursor()
    cur.execute(f'PRAGMA user_version = {SCHEMA_LATEST}')
    cur.execute('CREATE TABLE model(\
                id TEXT PRIMARY KEY,\
                runName TEXT,\
                botName TEXT,\
                created TEXT,\
                mu NUM,\
                sigma NUM,\
                steps INT,\
                locationType TEXT,\
                locationValue TEXT)')
    cur.execute('CREATE TABLE setting(key TEXT, val TEXT)')
    cur.execute('INSERT INTO model VALUES ("atba", "atba", "atba", ?, 0, 8.333, 0, "n/a", "n/a")', (now,))
    cur.execute('INSERT INTO setting VALUES ("ts_anchor", ?)', (defaults.get('ts_anchor', 'atba'),))
    db.commit()
    cur.close()
    db.close()

class RCubedDB:
    def __init__(self, fpath: str):
        if not os.path.exists(fpath):
            print("Database does not exist. Creating new database.")
            init_db(fpath)
        self._db = sqlite3.connect(fpath)
        cur = self._db.execute('PRAGMA user_version')
        version = cur.fetchone()[0]
        cur.close()
        if version != SCHEMA_LATEST:
            print(f"Database version is out of date. Expected {SCHEMA_LATEST}, got {version}")
            exit(-1)

        self.page_size = 50

    def get_models(self, page: int=0, run: str=None, bot: str=None) -> list:
        condition_data = []
        conditions = []
        if run is not None:
            conditions.append('runName = ?')
            condition_data.append(run)
        if bot is not None:
            conditions.append('botName = ?')
            condition_data.append(bot)
        cur = self._db.execute(
f'''SELECT id, runName, botName, created, mu, sigma, steps, locationType, locationValue
FROM model
{'WHERE ' + ' AND '.join(conditions) if len(conditions) > 0 else ''}
LIMIT ?, ?;
''', (*condition_data, page * self.page_size, self.page_size))
        rows = cur.fetchall()
        models = [
            {
                "id": row[0],
                "runName": row[1],
                "botName": row[2],
                "created": row[3],
                "ts": {
                    "mu": row[4],
                    "sigma": row[5],
                },
                "steps": row[6],
                "location": {
                    "type": row[7],
                    "value": row[8]
                }
            }
            for row in rows
        ]
        self._db.commit()
        cur.close()
        return models
    
    def get_num_models(self) -> int:
        cur = self._db.execute('SELECT COUNT(*) FROM model')
        num = cur.fetchone()[0]
        cur.close()
        return num

    def create_model(
        self,
        run_name: str,
        bot_name: str,
        location_type: str,
        location_value: str,
        steps: Optional[int]=None
    ):
        model_id = uuid4()
        created = datetime.now().isoformat()
        # If there is a previous model with the same run and bot name,
        # inherit its trueskill
        cur = self._db.execute(
'''SELECT mu, sigma FROM model
WHERE runName = ? AND botName = ?
ORDER BY steps, created DESC
LIMIT 1
''',
        (run_name, bot_name))
        # defaults from https://trueskill.org/#rating-the-model-for-skill
        mu, sigma = cur.fetchone() or (25, 25 / 3)
        cur.execute(
            'INSERT INTO model VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (str(model_id), run_name, bot_name, created, mu, sigma, steps, location_type, location_value)
        )
        self._db.commit()
        cur.close()
        return {"id": str(model_id), "ts": {"mu": mu, "sigma": sigma}}
    
    def get_model(self, model_id: str):
        cur = self._db.execute(
'''SELECT id, runName, botName, created, mu, sigma, steps, locationType, locationValue
FROM model
WHERE id = ?
''', (model_id,))
        row = cur.fetchone()
        cur.close()
        return row and {
            "id": row[0],
            "runName": row[1],
            "botName": row[2],
            "created": row[3],
            "ts": {
                "mu": row[4],
                "sigma": row[5],
            },
            "steps": row[6],
            "location": {
                "type": row[7],
                "value": row[8]
            }
        }

    def update_model(
        self,
        model_id: str,
        run_name: str=None,
        bot_name: str=None,
        location_type: str=None,
        location_value: str=None,
        ts: Dict[str, Any]=None,
        steps: int=None
    ):
        updates = []
        update_values = []
        if run_name:
            updates.append('runName = ?')
            update_values.append(run_name)
        if bot_name:
            updates.append('botName = ?')
            update_values.append(bot_name)
        if ts and 'mu' in ts.keys():
            updates.append('mu = ?')
            update_values.append(ts['mu'])
        if ts and 'sigma' in ts.keys():
            updates.append('sigma = ?')
            update_values.append(ts['sigma'])
        if steps:
            updates.append('steps = ?')
            update_values.append(steps)
        if location_type:
            updates.append('updateType = ?')
            update_values.append(location_type)
        if location_value:
            updates.append('locationValue = ?')
            update_values.append(location_value)
        if len(updates) == 0:
            return
        cur = self._db.execute(
f'''UPDATE model
SET {', '.join(updates)}
WHERE id = ?
''', (*update_values, model_id)
        )
        self._db.commit()
        cur.close()

    def delete_model(self, model_id: str) -> Tuple[str, float]:
        cur = self._db.execute('DELETE FROM model WHERE id = ?', (model_id,))
        self._db.commit()
        cur.close()

    def get_by_mu(self, mu, model_filter: Dict[str, List[str]], limit=50) -> List[Tuple[str, float, float, float]]:
        conditions = []
        values = []
        for botName, runNames in model_filter.items():
            conditions.append(f'botName = ? AND runName IN ({", ".join(["?"] * len(runNames))})')
            values.extend([botName, *runNames])
        cur = self._db.execute(
f'''SELECT id, ABS(mu - ?) AS dmu, mu, sigma
FROM model
WHERE {' OR '.join(conditions)}
ORDER BY dmu
LIMIT ?
''',
        (mu, *values, limit))
        opps = cur.fetchall()
        cur.close()
        return opps

    def get_by_sigma(self, model_filter: Dict[str, List[str]], limit=10) -> List[Tuple[str, float, float]]:
        conditions = []
        values = []
        for botName, runNames in model_filter.items():
            conditions.append(f'botName = ? AND runName IN ({", ".join(["?"] * len(runNames))})')
            values.extend([botName, *runNames])
        cur = self._db.execute(
f'''SELECT id, mu, sigma
FROM model
WHERE {' OR '.join(conditions)}
ORDER BY sigma DESC
LIMIT ?
''',
        (*values, limit))
        values = cur.fetchall()
        cur.close()
        return values

    
    def get_setting(self, key) -> str:
        cur = self._db.execute('SELECT val FROM setting WHERE key = ?', (key,))
        val = cur.fetchone()[0]
        cur.close()
        return val

    
    def close(self):
        self._db.close()
        self._db = None
        