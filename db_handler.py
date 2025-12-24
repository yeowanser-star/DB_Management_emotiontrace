# 专门负责 MySQL 的连接和所有 SQL 语句的执行。
import mysql.connector
from mysql.connector import pooling
import json


class DBHandler:
    def __init__(self, config):
        self.config = config
        try:
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="mypool",
                pool_size=10,
                pool_reset_session=True,
                **config
            )
            print("连接池初始化成功")
        except Exception as e:
            print(f"创建连接池失败: {e}")

    def _get_conn_and_cursor(self):
        conn = self.pool.get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        return conn, cursor

    def save_video_context(self, video_id, title, desc):
        # 强制转换类型
        video_id = str(video_id)

        conn, cursor = self._get_conn_and_cursor()
        query = """
        INSERT INTO videos (video_id, title, description)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE title=VALUES(title), description=VALUES(description)
        """
        try:
            cursor.execute(query, (video_id, title, desc))
            conn.commit()
        except Exception as e:
            print(f"写入视频元数据失败: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def save_comments_batch(self, video_id, comments_list):
        if not comments_list:
            return

        conn, cursor = self._get_conn_and_cursor()
        try:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            conn.start_transaction()

            sql_comment = """
            INSERT INTO comments (rpid, video_id, parent_id, uname, content, sentiment_score, relevance_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                sentiment_score=VALUES(sentiment_score), 
                relevance_score=VALUES(relevance_score)
            """

            batch_data = []
            for c in comments_list:
                raw_score = float(c['analysis'].get('score', 0.5))
                safe_score = max(0.01, min(0.99, raw_score))

                batch_data.append((
                    str(c['rpid']),
                    str(video_id),
                    str(c['parent_id']) if c.get('parent_id') else None,
                    c['uname'],
                    c['content'],
                    safe_score,
                    float(c['analysis'].get('relevance', 0.5))
                ))

            cursor.executemany(sql_comment, batch_data)

            for c in comments_list:
                try:
                    tags = c['analysis'].get('tags', [])
                    for tag_name in tags:
                        cursor.execute("INSERT IGNORE INTO tags_dict (tag_name) VALUES (%s)", (tag_name,))
                        cursor.execute("SELECT tag_id FROM tags_dict WHERE tag_name = %s", (tag_name,))
                        tag_res = cursor.fetchone()
                        if tag_res:
                            cursor.execute("INSERT IGNORE INTO comment_tag_map (rpid, tag_id) VALUES (%s, %s)",
                                           (str(c['rpid']), tag_res['tag_id']))
                except Exception as tag_e:
                    continue

            conn.commit()
            print(f">>> 成功同步 {len(comments_list)} 条评论（含外键容错处理）")

        except Exception as e:
            conn.rollback()
            print(f"❌ 批量同步严重失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            cursor.close()
            conn.close()
    def execute_query(self, query, params=None):

        conn, cursor = self._get_conn_and_cursor()
        try:
            cursor.execute(query, params or ())
            if cursor.with_rows:
                return cursor.fetchall()
            conn.commit()
            return None
        except Exception as e:
            print(f"SQL执行失败: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_video_stats(self, video_id):
        safe_vid = str(video_id)

        conn, cursor = self._get_conn_and_cursor()
        query = "SELECT avg_sentiment FROM videos WHERE video_id = %s"

        try:
            cursor.execute(query, (safe_vid,))
            result = cursor.fetchone()

            if result and result.get('avg_sentiment') is not None:
                return result
            else:
                return {"avg_sentiment": 0.5}

        except Exception as e:
            print(f"获取视频统计失败: {e}")
            return {"avg_sentiment": 0.5}
        finally:
            cursor.close()
            conn.close()

    def get_analysis_report(self, video_id):
        query = "SELECT * FROM view_comment_analysis WHERE video_id = %s"
        return self.execute_query(query, (str(video_id),))

# 实例化
from config import DB_CONFIG
db_handler = DBHandler(DB_CONFIG)