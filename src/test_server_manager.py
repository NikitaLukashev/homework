from common.config import CONFIG
from common.db_service import DBService
from common.logger import logger
from manager.manager import Manager
from model import Snapshot
from model import Catalog
from model import Prediction

from fixture import prediction_fixture
from server import Server

db_service = DBService(CONFIG['DATABASE'])
db_session = db_service.db_session
engine = db_service.engine


def reset_db_to_after_all_migration(engine_) -> None:
    """
    Create  base table after all migrations
    :param engine_:
    :return:
    """
    Prediction.__table__.drop(engine_)
    Snapshot.__table__.drop(engine_)

    Snapshot.__table__.create(engine_)
    Prediction.__table__.create(engine_)
    return


def test_db_contains_data():
    logger.info('After migration, catalog table contains data for training our model')

    reset_db_to_after_all_migration(engine)
    assert db_session.query(Catalog.id).count() == 8880
    db_service.close_db()


def test_manager_create_initial_model_if_no_model():
    logger.info('Instanciate manager without trained model.'
                ' Initial db contains Catalog data for training'
                ' An ml algorithm is trained and his snapshot is inserted into the empty '
                'db with an id equals to 1')

    reset_db_to_after_all_migration(engine)

    manager = Manager(db_session, engine, logger)
    assert db_session.query(Snapshot).count() == 1
    assert db_session.query(Snapshot.id).first()[0] == 1
    db_service.close_db()


def test_manager_take_initial_model_if_present():
    logger.info('Instanciate manager without trained model.'
                ' An ml algorithm is trained and his snapshot is inserted into the db with an id equals to 1.'
                'Instanciate a second manager, it will take the trained model by previous without'
                ' retrain.')
    reset_db_to_after_all_migration(engine)

    manager_1 = Manager(db_session, engine, logger)
    manager_2 = Manager(db_session, engine, logger)

    last_state = manager_2.algorithm_id

    assert db_session.query(Snapshot.id).order_by(Snapshot.id.desc()).first()[0] == last_state
    assert db_session.query(Snapshot).count() == 1
    assert db_session.query(Snapshot.id).first()[0] == 1
    db_service.close_db()


def test_manager_train():
    logger.info('Instanciate manager without trained model.'
                ' An ml algorithm is trained and his snapshot is inserted into the db with an id equals to 1.'
                'Train the algorithm, it will insert a new snapshot of the algorithm into the db with a new id 2')

    manager_1 = Manager(db_session, engine, logger)
    manager_1.train()

    assert db_session.query(Snapshot).count() == 2
    assert db_session.query(Snapshot.id).order_by(Snapshot.id.desc()).first()[0] == 2
    db_service.close_db()


def test_manager_predict():
    logger.info('Instanciate manager.'
                ' Predict on a fixture of input. '
                'Algorythm insert prediction into the db table predictions.'
                'Predicted output is of type dictionary with key as 0, 1, 2 '
                'and values as probability for each classes with sum equals to 1')

    manager = Manager(db_session, engine, logger)
    intial_number_prediction = db_session.query(Prediction.id).count()
    manager.predict(prediction_fixture)

    assert db_session.query(Prediction.id).count() == intial_number_prediction + 1
    assert isinstance(db_session.query(Prediction.prediction).order_by(Prediction.id.desc()).first()[0], dict)
    assert set(db_session.query(Prediction.prediction).order_by(Prediction.id.desc()).first()[0].keys()) == {'0', '1', '2'}
    assert sum(db_session.query(Prediction.prediction).order_by(Prediction.id.desc()).first()[0].values()) == 1
    db_service.close_db()


def test_manager_get_state():
    logger.info('Instantiate manager, it will take the last model in the db'
                ' or retrain one if there isn t.'
                'Retrieve the last state from the manager algorithm and the db. They should be equal'
                )

    manager = Manager(db_session, engine, logger)
    initial_state = manager.algorithm_id

    assert db_session.query(Snapshot.id).order_by(Snapshot.id.desc()).first()[0] == initial_state
    db_service.close_db()


def test_server_train():
    logger.info('Assert /train route respond with 200 when called and '
                'a new model is inserted into db with an incremental id')

    reset_db_to_after_all_migration(engine)

    manager = Manager(db_session, engine, logger)
    server = Server(manager, logger)
    client = server.test()

    train_res = client.post('/train')

    assert db_session.query(Snapshot).count() == 2
    assert db_session.query(Snapshot.id).order_by(Snapshot.id.asc()).first()[0] == 1
    assert db_session.query(Snapshot.id).order_by(Snapshot.id.desc()).first()[0] == 2
    assert train_res.status_code == 200
    db_service.close_db()


def test_server_predict():
    logger.info('Assert /predict route respond with 200 when called with a fixture')

    reset_db_to_after_all_migration(engine)

    manager = Manager(db_session, engine, logger)
    server = Server(manager, logger)
    client = server.test()

    predict_res = client.post('/predict', json=prediction_fixture)

    assert predict_res.status_code == 200
    assert db_session.query(Prediction.id).count() == 1
    db_service.close_db()


def test_server_state():
    logger.info('Assert /state route respond with 200 when called and return'
                ' the id and the creation date of the model'
                'Assert state is of the algorythme and stocked in the db is '
                'updated when a train occurs')

    reset_db_to_after_all_migration(engine)

    manager = Manager(db_session, engine, logger)
    server = Server(manager, logger)
    client = server.test()

    state_res = client.get('/state')

    assert db_session.query(Snapshot.id).first()[0] == manager.algorithm_id
    client.post('/train')

    assert db_session.query(Snapshot.id).order_by(Snapshot.id.desc()).first()[0] == manager.algorithm_id
    assert db_session.query(Snapshot.id).order_by(Snapshot.id.desc()).first()[0] == 2
    assert state_res.status_code == 200
    db_service.close_db()
