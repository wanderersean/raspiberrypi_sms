import logging

logger = logging.getLogger('sms')
logger.setLevel(level=logging.DEBUG)

# 配置文件logger
handler = logging.FileHandler("log.txt")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(filename)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 配置控制台logger
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(filename)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)

# 配对
logger.addHandler(handler)
logger.addHandler(console)


if __name__ == '__main__':
    logger.debug("hello world")