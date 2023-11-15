# 京东预约脚本
import sys

from jd_logger import logger
from jd_seckill import JdSeckill

if __name__ == '__main__':
    logger.info("开始执行脚本，参数为：" + str(sys.argv))
    sku_id = ''
    is_appoint = 0
    plan = 0
    if len(sys.argv) > 1:
        is_appoint = int(sys.argv[1])

    if len(sys.argv) > 2:
        sku_id = sys.argv[2]

    if len(sys.argv) > 3:
        plan = int(sys.argv[3])

    jd_seckill = JdSeckill(sku_id, plan)
    if is_appoint == 0:
        jd_seckill.make_reserve()
    else:
        jd_seckill.seckill_by_proc_pool()
