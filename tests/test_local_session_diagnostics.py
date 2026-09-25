import logging

import session_manager


def test_file_error_alert_is_written_to_local_session_log(tmp_path, monkeypatch):
    monkeypatch.setattr(session_manager, "get_log_path", lambda name: str(tmp_path / name))
    logger = logging.getLogger("SerrebiTorrent.session")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    alert = type("file_error_alert", (), {"message": lambda self: "disk full"})()
    session_manager.SessionManager.__new__(session_manager.SessionManager)._log_diagnostic_alert(alert)

    assert "disk full" in (tmp_path / "session.log").read_text(encoding="utf-8")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


def test_port_mapping_alerts_are_written_to_local_session_log(tmp_path, monkeypatch):
    monkeypatch.setattr(session_manager, "get_log_path", lambda name: str(tmp_path / name))
    logger = logging.getLogger("SerrebiTorrent.session")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    manager = session_manager.SessionManager.__new__(session_manager.SessionManager)
    for kind, text in (("portmap_alert", "UPnP mapped 6881"), ("portmap_error_alert", "UPnP no router")):
        manager._log_diagnostic_alert(type(kind, (), {"message": lambda self, t=text: t})())

    log = (tmp_path / "session.log").read_text(encoding="utf-8")
    assert "UPnP mapped 6881" in log and "UPnP no router" in log
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
