import redis

redisClient = redis.StrictRedis(host='redis', port=6379, decode_responses=True)
#redis server