import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta

from SignUtils import SignUtils
from SpiderSession import SpiderSession
from config import global_config
from jd_logger import logger
import util


class JdSeckill(object):

    def __init__(self, sku_id, plan):
        self.signUtils = SignUtils()
        self.spider_session = SpiderSession()

        self.d_model = global_config.getRaw('config', 'd_model')
        self.d_brand = global_config.getRaw('config', 'd_brand')
        self.client = global_config.getRaw('config', 'client')
        self.client_version = global_config.getRaw('config', 'client_version')
        self.eid = global_config.getRaw('config', 'eid')

        self.plan = plan

        self.sku_id = sku_id
        if self.sku_id == '':
            self.sku_id = global_config.getRaw('config', 'sku_id')
        self.seckill_num = 1
        self.seckill_init_info = dict()
        self.seckill_url = dict()
        self.seckill_order_data = dict()
        self.seckill_m_url = ''

        self.session = self.spider_session.get_session()
        self.user_agent = self.spider_session.user_agent

        self.running_flag = False
        self.stop_flag = True

    def make_reserve(self):
        """商品预约"""
        logger.info('商品:{}'.format(self.sku_id))
        url = 'https://api.m.jd.com/client.action?functionId=appoint'
        body = '{"autoAddCart":"0","bsid":"","check":"0","ctext":"","isShowCode":"0","mad":"0","skuId":"%s","type":"4"}' % self.sku_id
        sign_dict = self.signUtils.gen_sign('appoint', body)
        payload = {
            'ep': self.signUtils.gen_cipher_ep(),
            'st': sign_dict['st'],
            'sign': sign_dict['sign'],
            'sv': sign_dict['sv'],
            'body': body,
            'avifSupport': 0,
            'build': 168919,
            'client': self.client,
            'clientVersion': self.client_version,
            'd_brand': self.d_brand,
            'd_model': self.d_model,
            'ef': 1,
            'eid': self.eid,
            'ext': '{"prstate":"0","pvcStu":"1"}',
            'isBackground': 'N',
            'joycious': 37,
            'lang': 'zh_CN',
            'networkType': 'wifi',
            'networklibtype': 'JDNetworkBaseAF',
            'partner': 'apple',
            'rfs': '0000',
            'scope': '01',
            'uemps': '0-0-0'
        }

        resp = self.session.post(url=url, params=payload)
        resp_json = util.parse_json(resp.text)

        try:
            if resp_json['title'] == '您已成功预约，无需重复预约' or resp_json['title'] == '预约成功！':
                logger.info(resp_json['title'])
            else:
                logger.error('预约失败:' + resp_json)
        except Exception as e:
            logger.error('预约失败:' + resp.text)

    def seckill_by_proc_pool(self):
        """
        多进程进行抢购
        work_count：进程数量
        """
        # 增加进程配置
        work_count = int(global_config.getRaw('config', 'work_count'))
        with ProcessPoolExecutor(work_count) as pool:
            for i in range(work_count):
                pool.submit(self.seckill())

    def seckill_canstill_running(self):
        """
        计算开始时间
        :return:
        """
        buy_time = util.get_seckill_plan(self.plan)
        continue_time = self.local_jd_time_diff() - 50
        start_time = datetime.strptime(
            (datetime.strptime(buy_time, "%H:%M:%S.%f") + timedelta(milliseconds=continue_time)).strftime(
                "%H:%M:%S.%f"),
            "%H:%M:%S.%f"
        ).strftime("%H:%M:%S.%f")
        current_time = datetime.now().strftime("%H:%M:%S.%f")
        if current_time > start_time:
            self.running_flag = True
            self.stop_flag = True

    def seckill(self):
        """
        抢购
        """
        while self.stop_flag:
            # 判断是否开始
            self.seckill_canstill_running()
            while self.running_flag:
                try:
                    # 获取抢购链接
                    self.request_seckill_url()
                    # 访问抢购结算链接
                    self.request_seckill_checkout_page()
                    # 提交订单
                    self.submit_seckill_order()
                except Exception as e:
                    logger.info('抢购发生异常，稍后继续执行！' + str(e))
                # 判断是否停止
                self.seckill_canstill_stop()
                # util.wait_some_time()

    def seckill_canstill_stop(self):
        """用config.ini文件中的continue_time加上函数buytime_get()获取到的buy_time，
            来判断抢购的任务是否可以继续运行
        """
        buy_time = util.get_seckill_plan(self.plan)
        continue_time = int(global_config.getRaw('config', 'continue_time'))
        stop_time = datetime.strptime(
            (datetime.strptime(buy_time, "%H:%M:%S.%f") + timedelta(seconds=continue_time)).strftime("%H:%M:%S.%f"),
            "%H:%M:%S.%f"
        ).strftime("%H:%M:%S.%f")
        current_time = datetime.now().strftime("%H:%M:%S.%f")
        if current_time > stop_time:
            self.running_flag = False
            self.stop_flag = False
            logger.info('超过允许的运行时间，任务结束。')

    def reset_headers(self):
        self.session.headers = self.spider_session.get_headers()

    def gen_token(self):
        """
        获取商品的抢购链接的跳转链接
        :return: 商品的抢购链接
        """
        url = 'https://api.m.jd.com/client.action?functionId=genToken'
        body = '{"to":"https://divide.jd.com/user_routing?skuId=%s&from=app","action":"to"}' % self.sku_id
        sign_dict = self.signUtils.gen_sign('genToken', body)
        payload = {
            'ep': self.signUtils.gen_cipher_ep(),
            'st': sign_dict['st'],
            'sign': sign_dict['sign'],
            'sv': sign_dict['sv'],
            'body': body,
            'avifSupport': 0,
            'build': 168919,
            'client': self.client,
            'clientVersion': self.client_version,
            'd_brand': self.d_brand,
            'd_model': self.d_model,
            'ef': 1,
            'eid': self.eid,
            'ext': '{"prstate":"0","pvcStu":"1"}',
            'isBackground': 'N',
            'joycious': 37,
            'lang': 'zh_CN',
            'networkType': 'wifi',
            'networklibtype': 'JDNetworkBaseAF',
            'partner': 'apple',
            'rfs': '0000',
            'scope': '01',
            'uemps': '0-0-0'
        }

        resp = self.session.get(url=url, params=payload)
        appjmp_url = ''
        logger.info(resp.text)
        if util.response_status(resp):
            token_params = resp.json()
            if token_params['code'] == '0':
                appjmp_url = '%s?tokenKey=%s&to=https://divide.jd.com/user_routing?skuId=%s&from=app' % (
                    token_params['url'], token_params['tokenKey'], self.sku_id)
                logger.info('生成抢购链接：' + appjmp_url)
        return appjmp_url

    def jump_url(self, url):
        router_url = ''
        if url != '':
            resp = self.session.get(url=url, allow_redirects=False)
            if resp.headers.get('location'):
                # https://divide.jd.com/user_routing?skuId=100012043978&from=app&mid=D3zc_MpmYJHxTIc63q3e4fmvV4DTiYMh48h-EW5HKvk&sid=
                # https://marathon.jd.com/m/captcha.html?sid=&from=app&skuId=100012043978&mid=D3zc_MpmYJHxTIc63q3e4fmvV4DTiYMh48h-EW5HKvk
                router_url = resp.headers.get('location')
                if resp.headers.get('Set-Cookie'):
                    self.session.headers['Cookie'] = self.session.headers.get('Cookie') + ';' + resp.headers.get(
                        'Set-Cookie')
        return router_url

    def get_seckill_url(self):
        """
        获取商品的抢购链接
        点击"抢购"按钮后，会有两次302跳转，最后到达订单结算页面
        这里返回第一次跳转后的页面url，作为商品的抢购链接
        :return: 商品的抢购链接
        """
        while True:
            # 重置请求头 请求设备 Cookie
            self.reset_headers()
            url = self.gen_token()
            seckill_url = self.jump_url(self.jump_url(url))
            if seckill_url != '':
                logger.info("抢购链接获取成功: %s", seckill_url)
                return seckill_url
            else:
                logger.info("抢购链接获取失败，稍后自动重试")
                util.wait_some_time()

    def request_seckill_url(self):
        """访问商品的抢购链接（用于设置cookie等"""
        logger.info('商品:{}'.format(self.sku_id))
        self.seckill_url[self.sku_id] = self.get_seckill_url()
        logger.info('访问商品的抢购连接...')
        resp = self.session.get(url=self.seckill_url[self.sku_id], allow_redirects=False)
        if resp.headers.get('location') and resp.headers.get('location') != '' and resp.headers.get('location') != 'https://marathon.jd.com/mobile/koFail.html':
            # https://marathon.jd.com/mobile/koFail.html
            self.seckill_m_url = resp.headers.get('location')
            if resp.headers.get('Set-Cookie'):
                self.session.headers['Cookie'] = self.session.headers.get('Cookie') + ';' + resp.headers.get(
                    'Set-Cookie')
        else:
            raise Exception('抢购失败：' + resp.headers.get('location'))

    def request_seckill_checkout_page(self):
        """访问抢购订单结算页面"""
        logger.info('访问抢购订单结算页面...' + self.seckill_m_url)
        resp = self.session.get(url=self.seckill_m_url, allow_redirects=False)
        if resp.headers.get('Set-Cookie'):
            self.session.headers['Cookie'] = self.session.headers.get('Cookie') + ';' + resp.headers.get(
                'Set-Cookie')
        else:
            raise Exception('抢购订单结算页面访问失败，正在重试...')

    def _get_seckill_init_info(self):
        """获取秒杀初始化信息（包括：地址，发票，token）
        :return: 初始化信息组成的dict
        """
        logger.info('获取秒杀初始化信息...')
        url = 'https://marathon.jd.com/seckillnew/orderService/init.action'

        payload = {
            'sku': self.sku_id,
            'num': self.seckill_num,
            'deliveryMode': '',
            'id': '8664739556',
            'provinceId': '4',
            'cityId': '50950',
            'countyId': '58472',
            'townId': '0',
        }
        resp = self.session.post(url=url, data=payload)
        logger.info('获取秒杀初始化信息返回内容：' + str(resp.text))
        try:
            resp_json = util.parse_json(resp.text)
            return resp_json
        except Exception:
            logger.info('获取秒杀初始化信息失败，正在重试...')
            # return self._get_seckill_init_info()
            raise Exception('获取秒杀初始化信息失败，正在重试...')

    def _get_seckill_order_data(self):
        """生成提交抢购订单所需的请求体参数
        :return: 请求体参数组成的dict
        """
        logger.info('生成提交抢购订单所需参数...')
        # 获取用户秒杀初始化信息
        self.seckill_init_info[self.sku_id] = self._get_seckill_init_info()
        init_info = self.seckill_init_info.get(self.sku_id)
        default_address = init_info['address']  # 默认地址dict
        invoice_info = init_info['invoiceInfo']  # 默认发票信息dict, 有可能不返回
        token = init_info['token']

        data = {
            'num': init_info['seckillSkuVO']['num'],
            'addressId': default_address['id'],
            'name': default_address['name'],
            'provinceId': default_address['provinceId'],
            'provinceName': default_address['provinceName'],
            'cityId': default_address['cityId'],
            'cityName': default_address['cityName'],
            'countyId': default_address['countyId'],
            'countyName': default_address['countyName'],
            'townId': default_address['townId'],
            'townName': default_address['townName'],
            'addressDetail': default_address['addressDetail'],
            'mobile': default_address['mobile'],
            'mobileKey': default_address['mobileKey'],
            'email': '',
            'invoiceTitle': invoice_info['invoiceTitle'],
            'invoiceContent': invoice_info['invoiceContentType'],
            'invoicePhone': invoice_info['invoicePhone'],
            'invoicePhoneKey': invoice_info['invoicePhoneKey'],
            'invoice': True,
            'password': '',
            'codTimeType': '3',
            'paymentType': '4',
            'overseas': '0',
            'phone': '',
            'areaCode': default_address['areaCode'],
            'token': token,
            'skuId': self.sku_id,
            'eid': self.eid
        }
        return data

    def submit_seckill_order(self):
        """提交抢购（秒杀）订单
        :return: 抢购结果 True/False
        """
        url = 'https://marathon.jd.com/seckillnew/orderService/submitOrder.action?skuId=%s' % self.sku_id

        try:
            self.seckill_order_data[self.sku_id] = self._get_seckill_order_data()
        except Exception as e:
            raise Exception('抢购失败，无法获取生成订单的基本信息，接口返回:【{}】'.format(str(e)))

        logger.info('提交抢购订单...')
        # 修改设置请求头的方式
        self.session.headers['x-rp-client'] = 'h5_1.0.0'
        self.session.headers['x-referer-page'] = 'https://marathon.jd.com/seckillM/seckill.action'
        self.session.headers['origin'] = 'https://marathon.jd.com'
        self.session.headers['Referer'] = 'https://marathon.jd.com/seckillM/seckill.action?skuId={0}&num={1}&rid={2}&deliveryMode='.format(
            self.sku_id, self.seckill_num, int(time.time()))
        # 防止重定向，增加allow_redirects=False，20210107
        resp = self.session.post(
            url=url,
            data=self.seckill_order_data.get(
                self.sku_id),
            allow_redirects=False)
        logger.info(resp.text)
        try:
            # 解析json
            resp_json = util.parse_json(resp.text)
            # 返回信息
            # 抢购失败：
            # {'errorMessage': '很遗憾没有抢到，再接再厉哦。', 'orderId': 0, 'resultCode': 60074, 'skuId': 0, 'success': False}
            # {'errorMessage': '抱歉，您提交过快，请稍后再提交订单！', 'orderId': 0, 'resultCode': 60017, 'skuId': 0, 'success': False}
            # {'errorMessage': '系统正在开小差，请重试~~', 'orderId': 0, 'resultCode': 90013, 'skuId': 0, 'success': False}
            # 抢购成功：
            # {"appUrl":"xxxxx","orderId":820227xxxxx,"pcUrl":"xxxxx","resultCode":0,"skuId":0,"success":true,"totalMoney":"xxxxx"}
            if resp_json.get('success'):
                order_id = resp_json.get('orderId')
                total_money = resp_json.get('totalMoney')
                pay_url = 'https:' + resp_json.get('pcUrl')
                logger.info('抢购成功，订单号:{}, 总价:{}, 电脑端付款链接:{}'.format(order_id, total_money, pay_url))
                if global_config.getRaw('messenger', 'server_chan_enable') == 'true':
                    success_message = "抢购成功，订单号:{}, 总价:{}, 电脑端付款链接:{}".format(order_id, total_money, pay_url)
                    # send_wechat(success_message)
                    self.running_flag = False
                return True
            else:
                logger.info('抢购失败，返回信息:{}'.format(resp_json))
                if global_config.getRaw('messenger', 'server_chan_enable') == 'true':
                    error_message = '抢购失败，返回信息:{}'.format(resp_json)
                    # send_wechat(error_message)
                return False
        except Exception as e:
            raise Exception('抢购失败，返回信息:{}'.format(resp.text[0: 128]))

    def jd_time(self):
        """
        从京东服务器获取时间戳
        :return:
        """
        url = 'https://api.m.jd.com'
        resp = self.session.get(url)
        jd_timestamp = int(resp.headers.get('X-API-Request-Id')[-13:])
        return jd_timestamp

    def local_time(self):
        """
        获取本地时间戳
        """
        local_timestamp = round(time.time() * 1000)
        return local_timestamp

    def local_jd_time_diff(self):
        """
        计算本地与京东服务器时间差
        """
        return self.local_time() - self.jd_time()
