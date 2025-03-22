import custom_mysql


class CrawlerPipeline:
    def process_item(self, item, spider):
        return item


class MySQLPipeline(object):
    def __init__(self):
        # Database connection parameters
        self.host = 'localhost'
        self.user = 'root'
        self.password = '123456'  # Replace with your MySQL password
        self.database = 'sam_gov_data'  # Replace with your database name
        self.port = 3306

        # Connect to MySQL database
        self.connection = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            charset='utf8mb4'
        )

        # Create cursor
        self.cursor = self.connection.cursor()

        # Create database if it doesn't exist
        self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
        self.cursor.execute(f"USE {self.database}")

        # Create table if it doesn't exist
        self.create_table()

    def create_table(self):
        # Create a table to store the data
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sam_opportunities (
            id INT AUTO_INCREMENT PRIMARY KEY,
            publish_date VARCHAR(50),
            response_date VARCHAR(50),
            link VARCHAR(255),
            cot VARCHAR(100),
            osa VARCHAR(100),
            naics VARCHAR(50),
            department VARCHAR(255),
            title TEXT,
            notice_id VARCHAR(100),
            state VARCHAR(50),
            city VARCHAR(100),
            email VARCHAR(100),
            search_type VARCHAR(20),
            organization_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.cursor.execute(create_table_sql)
        self.connection.commit()

    def process_item(self, item, spider):
        # Insert data into MySQL table
        insert_sql = """
        INSERT INTO sam_opportunities (
            publish_date, response_date, link, cot, osa, naics, 
            department, title, notice_id, state, city, email, 
            search_type, organization_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            item['publishDate'],
            item['responseDate'],
            item['link'],
            item['cot'],
            item['osa'],
            item['naics'],
            item['department'],
            item['title'],
            item['noticeId'],
            item['state'],
            item['city'],
            item['email'],
            item['searchType'],
            item.get('organizationId', '-')  # Use get() method to handle possible KeyError
        )

        # Execute the query
        self.cursor.execute(insert_sql, values)
        self.connection.commit()

        return item

    def close_spider(self, spider):
        # Close the database connection when the spider is closed
        self.cursor.close()
        self.connection.close()