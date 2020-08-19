import json
import os

import humps

from visuanalytics.server.db import db

STEPS_LOCATION = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resources/steps"))


def get_topic_names():
    con = db.open_con_f()
    res = con.execute("SELECT steps_id, steps_name, json_file_name FROM steps")
    return [{"topicId": row["steps_id"], "topicName": row["steps_name"],
             "topicInfo": _get_topic_steps(row["json_file_name"]).get("info", "")} for row in res]


def get_params(topic_id):
    con = db.open_con_f()
    res = con.execute("SELECT json_file_name FROM steps WHERE steps_id = ?", [topic_id]).fetchone()
    if res is None:
        return None
    steps_json = _get_topic_steps(res["json_file_name"])
    run_config = steps_json["run_config"]
    return humps.camelize(_to_param_list(run_config))


def get_job_list():
    con = db.open_con_f()
    res = con.execute("""
        SELECT 
        job_id, job_name, 
        schedule.type, time, STRFTIME('%Y-%m-%d', date) as date, time_interval,
        delete_type, days, hours, k_count, fix_names_count,
        GROUP_CONCAT(DISTINCT weekday) AS weekdays,
        COUNT(DISTINCT position_id) AS topic_count,
        GROUP_CONCAT(DISTINCT steps.steps_id || ":" || steps_name || ":" || json_file_name || ":" || position) AS topic_positions,
        GROUP_CONCAT(DISTINCT position || ":" || key || ":" || value || ":" || job_config.type) AS param_values
        FROM job 
        INNER JOIN schedule USING (schedule_id)
        LEFT JOIN schedule_weekday USING (schedule_id)
        INNER JOIN job_topic_position USING (job_id) 
        LEFT JOIN job_config USING (position_id) 
        INNER JOIN steps USING (steps_id)
        GROUP BY (job_id)
    """)
    return [_row_to_job(row) for row in res]


def insert_job(job):
    con = db.open_con_f()
    job_name = job["jobName"]
    schedule = job["schedule"]
    delete_schedule = job["deleteSchedule"]
    topic_values = job["topics"]
    delete_type, days, hours, keep_count, fix_names_count = _unpack_delete_schedule(delete_schedule)

    schedule_id = _insert_schedule(con, schedule)

    job_id = con.execute(
        "INSERT INTO job(job_name, schedule_id, delete_type, days, hours, k_count, fix_names_count) "
        "VALUES(?, ?, ?, ?, ?, ?, ?)",
        [job_name, schedule_id, delete_type, days, hours, keep_count, fix_names_count]).lastrowid

    _insert_param_values(con, job_id, topic_values)
    con.commit()


def delete_job(job_id):
    con = db.open_con_f()
    con.execute("PRAGMA foreign_keys = ON")
    schedule_id = con.execute("SELECT schedule_id FROM job WHERE job_id=?", [job_id]).fetchone()["schedule_id"]
    con.execute("DELETE FROM schedule WHERE schedule_id=?", [schedule_id])
    con.commit()


def update_job(job_id, updated_data):
    con = db.open_con_f()
    for key, value in updated_data.items():
        if key == "jobName":
            con.execute("UPDATE job SET job_name=? WHERE job_id=?", [value, job_id])
        if key == "schedule":
            old_schedule_id = con.execute("SELECT schedule_id FROM job WHERE job_id=?", [job_id]).fetchone()[
                "schedule_id"]
            con.execute("DELETE FROM schedule WHERE schedule_id=?", [old_schedule_id])
            con.execute("DELETE FROM schedule_weekday WHERE schedule_id=?", [old_schedule_id])
            schedule_id = _insert_schedule(con, value)
            con.execute("UPDATE job SET schedule_id=? WHERE job_id=?", [schedule_id, job_id])
        if key == "deleteSchedule":
            delete_type, days, hours, keep_count, fix_names_count = _unpack_delete_schedule(value)
            con.execute("UPDATE job SET delete_type=?, days=?, hours=?, k_count=?, fix_names_count=? WHERE job_id=?",
                        [delete_type, days, hours, keep_count, fix_names_count, job_id])
        if key == "topics":
            pos_id_rows = con.execute("SELECT position_id FROM job_topic_position WHERE job_id=?", [job_id])
            pos_ids = [(row["position_id"],) for row in pos_id_rows]
            con.execute("DELETE FROM job_topic_position WHERE job_id=?", [job_id])
            con.executemany("DELETE FROM job_config WHERE position_id=?", pos_ids)
            _insert_param_values(con, job_id, value)
    con.commit()


def get_logs():
    con = db.open_con_f()
    logs = con.execute(
        "SELECT "
        "job_id, job_name, state, error_msg, error_traceback, duration, start_time "
        "from job_logs INNER JOIN job USING (job_id) "
        "ORDER BY job_logs_id DESC").fetchall()
    return [{
        "jobId": log["job_id"],
        "jobName": log["job_name"],
        "state": log["state"],
        "errorMsg": log["error_msg"],
        "errorTraceback": log["error_traceback"],
        "duration": log["duration"],
        "startTime": log["start_time"]
    }
        for log in logs]


def _insert_param_values(con, job_id, topic_values):
    for pos, t in enumerate(topic_values):
        position_id = con.execute("INSERT INTO job_topic_position(job_id, steps_id, position) VALUES (?, ?, ?)",
                                  [job_id, t["topicId"], pos]).lastrowid
        jtkvt = [(position_id,
                  k,
                  _to_untyped_value(v["value"], humps.decamelize(v["type"])),
                  humps.decamelize(v["type"]))
                 for k, v in t["values"].items()]
        con.executemany("INSERT INTO job_config(position_id, key, value, type) VALUES(?, ?, ?, ?)", jtkvt)


def _insert_schedule(con, schedule):
    type, time, date, weekdays, time_interval = _unpack_schedule(schedule)
    schedule_id = con.execute("INSERT INTO schedule(type, time, date, time_interval) VALUES (?, ?, ?, ?)",
                              [type, time, date, time_interval]).lastrowid
    if type == "weekly":
        id_weekdays = [(schedule_id, d) for d in weekdays]
        con.executemany("INSERT INTO schedule_weekday(schedule_id, weekday) VALUES(?, ?)", id_weekdays)
    return schedule_id


def _row_to_job(row):
    job_id = row["job_id"]
    job_name = row["job_name"]
    weekdays = str(row["weekdays"]).split(",") if row["weekdays"] is not None else []
    param_values = row["param_values"]

    type = row["type"]
    time = row["time"]
    schedule = {
        "type": humps.camelize(row["type"])
    }

    if type == "daily":
        schedule = {**schedule, "time": time}
    if type == "weekly":
        schedule = {**schedule, "time": time, "weekdays": [int(d) for d in weekdays]}
    if type == "on_date":
        schedule = {**schedule, "time": time, "date": row["date"]}
    if type == "interval":
        schedule = {**schedule, "interval": row["time_interval"]}

    delete_type = row["delete_type"]
    delete_schedule = {
        "type": humps.camelize(delete_type)
    }
    if delete_type == "on_day_hour":
        delete_schedule = {**delete_schedule, "removalTime": {"days": int(row["days"]), "hours": int(row["hours"])}}
    if delete_type == "keep_count":
        delete_schedule = {**delete_schedule, "keepCount": int(row["k_count"])}
    if delete_type == "fix_names":
        delete_schedule = {**delete_schedule, "count": int(row["fix_names_count"])}

    topics = [{}] * (int(row["topic_count"]))
    for tp_s in row["topic_positions"].split(","):
        tp = tp_s.split(":")
        topic_id = tp[0]
        topic_name = tp[1]
        json_file_name = tp[2]
        position = int(tp[3])
        run_config = _get_topic_steps(json_file_name)["run_config"]
        params = humps.camelize(_to_param_list(run_config))
        topics[position] = {
            "topicId": topic_id,
            "topicName": topic_name,
            "params": params,
            "values": {}
        }
    if param_values is not None:
        for vals_s in param_values.split(","):
            vals = vals_s.split(":")
            position = int(vals[0])
            name = vals[1]
            u_val = vals[2]
            type = vals[3]
            t_val = to_typed_value(u_val, type)
            topics[position]["values"] = {
                **topics[position]["values"],
                name: t_val
            }

    return {
        "jobId": job_id,
        "jobName": job_name,
        "schedule": schedule,
        "deleteSchedule": delete_schedule,
        "topicValues": topics
    }


def _get_topic_steps(json_file_name: str):
    path_to_json = os.path.join(STEPS_LOCATION, json_file_name) + ".json"
    with open(path_to_json, encoding="utf-8") as fh:
        return json.loads(fh.read())


def _get_values(param_string):
    if param_string is None:
        return []
    kvts = [kvt.split(":") for kvt in param_string.split(",")]
    values = {kvt[0]: to_typed_value(kvt[1], kvt[2]) for kvt in kvts}
    return values


def _to_untyped_value(v, t):
    if t in ["string", "enum"]:
        return v
    if t in ["multi_string"]:
        return ";".join(v)
    if t in ["multi_number"]:
        return ";".join([str(n) for n in v])
    if t in ["boolean", "sub_params", "number"]:
        return str(v)


def to_typed_value(v, t):
    if t in ["string", "enum"]:
        return v
    if t in ["number"]:
        if "." in v:
            return float(v)
        return int(v)
    if t in ["multi_string"]:
        return v.split(";")
    if t in ["multi_number"]:
        return [float(n) if "." in n else int(n) for n in v.split(";")]
    if t in ["boolean", "sub_params"]:
        return v == "True"


def _unpack_schedule(schedule):
    type = humps.decamelize(schedule["type"])
    time = schedule["time"] if type != "interval" else None
    date = schedule["date"] if type == "on_date" else None
    time_interval = schedule["timeInterval"] if type == "interval" else None
    weekdays = schedule["weekdays"] if type == "weekly" else None
    return type, time, date, weekdays, time_interval


def _unpack_delete_schedule(delete_schedule):
    delete_type = humps.decamelize(delete_schedule["type"])
    days = delete_schedule["removalTime"]["days"] if delete_type == "on_day_hour" else None
    hours = delete_schedule["removalTime"]["hours"] if delete_type == "on_day_hour" else None
    keep_count = delete_schedule["keepCount"] if delete_type == "keep_count" else None
    fix_names_count = delete_schedule["count"] if delete_type == "fix_names" else None
    return delete_type, days, hours, keep_count, fix_names_count


def _to_param_list(run_config):
    return [{**{"name": key},
             **({**value, "type": humps.camelize(value["type"])}
                if value["type"] != "sub_params"
                else {**value, "type": "subParams", "sub_params": _to_param_list(value["sub_params"])})}
            for key, value in run_config.items()]
