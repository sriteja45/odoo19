import redis
r = redis.Redis(
    host='redis.dealwallet.com', 
    port=6379, 
    password='redis123321',
    decode_responses=True
)
if r:
    print("Redis connection successful")
    print(r.ping())

r.set("name", "Jai Sri Rama")
print(r.get("name"))