from random import choices, randint, sample
from typing import Dict, List
from flask import Flask, request
from rcubed.server.db import RCubedDB
from trueskill import Rating, quality, rate

app = Flask(__name__)

@app.get('/models')
def get_models():
    page = request.args.get('page', 0)
    page = int(page) if page else 0
    run = request.args.get('run', None)
    bot = request.args.get('bot', None)
    db = RCubedDB(app.config['db'])
    models = db.get_models(page, run, bot)
    has_next_page = db.get_num_models() > 50 + 50 * page
    if has_next_page:
        return {"data": models, "nextPage": page + 1}
    else:
        return {"data": models}

@app.post('/models')
def create_model():
    model_stub = request.json
    db = RCubedDB(app.config['db'])
    partial_model = db.create_model(
        model_stub["runName"],
        model_stub["botName"],
        model_stub["location"]["type"],
        model_stub["location"]["value"],
        model_stub.get("steps", None)
    )
    return {**model_stub, **partial_model}, 201

@app.get('/models/<modelId>')
def get_model(modelId: str):
    db = RCubedDB(app.config['db'])
    model = db.get_model(modelId)
    if model is None:
        return {"error": f"No model with id {modelId}"}, 404
    return model

@app.patch('/models/<modelId>')
def update_model(modelId: str):
    update = request.json
    db = RCubedDB(app.config['db'])
    db.update_model(
        modelId,
        update.get('runName', None),
        update.get('botName', None),
        update.get('location') and update['location'].get('type', None),
        update.get('location') and update['location'].get('value', None),
        update.get('ts', None),
        update.get('steps', None)
    )
    return '', 204

@app.delete('/models/<modelId>')
def delete_model(modelId: str):
    db = RCubedDB(app.config['db'])
    db.delete_model(modelId)
    return '', 204

@app.post('/ts/match')
def get_match():
    body = request.json
    db = RCubedDB(app.config['db'])
    # Choose a model with high sigma to always include
    sigma_models = db.get_by_sigma(body["bots"])
    chosen = sigma_models[randint(0, len(sigma_models)-1)]
    # Get models that can participate (make sure chosen is first)
    models = [(chosen[0], 0, chosen[1], chosen[2])] + [m for m in db.get_by_mu(chosen[1], body["bots"], 20) if m[0] != chosen[0]]
    ratings = [Rating(m[2], m[3]) for m in models]
    n_models = len(models)
    # Find a fair matchup
    best_q = 0
    best_match = None
    for _ in range(10):
        candidate = [
            [0] + [randint(0, n_models-1) for _ in range(3-1)],
            [randint(0, n_models-1) for _ in range(3)],
        ]
        q = quality([[ratings[c] for c in candidate[0]], [ratings[c] for c in candidate[1]]])
        if q > best_q:
            best_q = q
            best_match = [[models[c][0] for c in candidate[0]], [models[c][0] for c in candidate[1]]]
    return {"team0": best_match[0], "team1": best_match[1]}

@app.post('/ts/result')
def post_result():
    body = request.json
    db = RCubedDB(app.config['db'])
    team0 = [db.get_model(m) for m in body["match"]["team0"]]
    team0 = [Rating(mu=m["ts"]["mu"], sigma=m["ts"]["sigma"]) for m in team0]
    team1 = [db.get_model(m) for m in body["match"]["team1"]]
    team1 = [Rating(mu=m["ts"]["mu"], sigma=m["ts"]["sigma"]) for m in team1]
    ts_anchor = db.get_setting('ts_anchor')
    # Lower is better, so 0 < 0.5 and 1 > 0.5
    updated_t0, updated_t1 = rate([team0, team1], [body["result"], 0.5])
    ratings: Dict[str, List[Rating]] = {}
    for rating, _id in zip(updated_t0 + updated_t1, body["match"]["team0"] + body["match"]["team1"]):
        # ts_anchor should never be updated
        if _id == ts_anchor:
            continue
        ratings.setdefault(_id, []).append(rating)
    
    for _id, rs in ratings.items():
        db.update_model(_id, ts={"mu": sum(r.mu for r in rs) / len(rs), "sigma": sum(r.sigma for r in rs)})

    return '', 204


@app.post('/ts/opponents')
def get_opponents():
    body = request.json
    db = RCubedDB(app.config['db'])
    models_with_dmu = db.get_by_mu(body['for']['mu'], body['bots'], max(50, body['numOpponents'] * 5))
    chosen = sample(models_with_dmu, min(body["numOpponents"], len(models_with_dmu)), counts=range(len(models_with_dmu), 0, -1))
    return [m[0] for m in chosen]
