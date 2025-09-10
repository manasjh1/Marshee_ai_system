import redis

def test_redis_connection():
    try:
        print("Testing Redis connection with exact Redis Cloud details...")
        
        r = redis.Redis(
            host='redis-15929.c330.asia-south1-1.gce.redns.redis-cloud.com',
            port=15929,
            decode_responses=True,
            username="default",
            password="M9wwYkpGDz7H2OUa9Yb2DBN8JKYEMz8k",
            socket_connect_timeout=30
        )
        
        print("Attempting to ping Redis...")
        result = r.ping()
        print(f"Ping successful: {result}")
        
        print("Testing set operation...")
        success = r.set('test_key', 'test_value')
        print(f"Set operation result: {success}")
        
        print("Testing get operation...")
        value = r.get('test_key')
        print(f"Retrieved value: {value}")
        
        print("Redis connection test PASSED!")
        return True
        
    except Exception as e:
        print(f"Redis connection test FAILED: {e}")
        return False

if __name__ == "__main__":
    test_redis_connection()