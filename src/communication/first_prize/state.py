# -*- coding: utf-8 -*-
# @Time       : 2020/10/1 19:21
# @Author     : Duofeng Wu
# @File       : gd_handle.py
# @Description: 鑷鍔ㄨВ鏋愭幖铔嬫墍鍙戦佹潵鐨凧SON鏁版嵁

class State(object):

    def __init__(self,name):

        """
        姣忎釜瀹炰緥鐨勪繚鎶ゅ睘鎬у瑰簲JSON涓鐨勫瓧娈靛硷紝绉佹湁灞炴ц〃绀烘牴鎹涓嶅悓type鍜宻tage杩涜屼笉鍚岃В鏋愩
        type:          琛ㄧず娑堟伅绫诲瀷銆傚彲鍙栧煎寘鎷琻otify鍜宎ct銆俷otify琛ㄧず閫氱煡绫诲瀷锛宎ct琛ㄧず鍔ㄤ綔绫诲瀷锛堝嵆鏀跺埌璇ョ被鍨嬬殑娑堟伅鏃堕渶瑕佸仛鍑哄姩浣滐級
        stage:         琛ㄧず娓告垙闃舵点傚彲鍙栧煎寘鎷琤eginning, play, tribute, anti-tribute, back, episodeOver, gameOver
                        鍒嗗埆瀵瑰簲寮濮嬮樁娈点佸嚭鐗岄樁娈点佽繘璐￠樁娈点佹姉璐￠樁娈点佽繕璐￠樁娈点佺粨鏉熼樁娈
        myPos:         琛ㄧず鑷宸辩殑搴т綅鍙
        publicInfo:    琛ㄧず娓告垙涓鐜╁跺叕鍏变俊鎭
        actionList:    琛ㄧず鍙琛岀殑鍔ㄤ綔鍒楄〃
        curAction:     琛ㄧず鏌愮帺瀹跺仛鍑虹殑鍔ㄤ綔
        curPos:        琛ㄧず鍋氬嚭褰撳墠鍔ㄤ綔鐨勭帺瀹剁殑搴т綅鍙
        greaterPos:    琛ㄧず鏈澶у姩浣滅殑鐜╁剁殑搴т綅鍙
        greaterAction: 琛ㄧず鏈澶у埌浣犲伐浣
        handCards:     琛ㄧず鎵嬬墝
        oppoRank:      琛ㄧず瀵规墜绛夌骇
        curRank:       琛ㄧず褰撳墠娓告垙鍦ㄤ娇鐢ㄧ殑绛夌骇None
        selfRank:      琛ㄧず鎴戞柟绛夌骇
        antiNum:       琛ㄧず鎶楄础浜烘暟
        antiPos:       琛ㄧず鎶楄础鐜╁讹紙浠锛夌殑 搴т綅鍙
        result:        琛ㄧず杩涜础鎴栬呰繕璐＄殑缁撴灉
        order:         琛ㄧず瀹岀墝鐨勬″簭
        curTimes:      褰撳墠鐨勫瑰眬娆℃暟
        settingTimes   璁惧畾鐨勫瑰眬娆℃暟
        victoryNum     琛ㄧず杈惧埌璁惧畾鍦烘℃椂鐨勬渶缁堢粨鏋滐紙鍝涓鏂硅耽寰楀氾級
        parse_func:    琛ㄧず鐢ㄤ簬瑙ｆ瀽鐨勫嚱鏁
        """

        # history = {'0': {'send': [], 'remain': 27}, ...{} 璁板綍鐢ㄦ埛鎵撳嚭鐨勭墝
        # remain_cards = [4 * 14] 璁板綍鐗屽簱鍓╀綑鐗
        # played_cards = {'0': [], ...{} 鏈杞鐢ㄦ埛鎵撳嚭鐨勭墝
        # player_id 鐢ㄦ埛id
        # current_hands = [] 褰撳墠鎵嬬墝
        # action_list 鍙鎵ц屽姩浣滃垪琛
        self.tribute_result = None
        self.history = {
            '0': {
                'send': [],
                'remain': 27,
            },
            '1': {
                'send': [],
                'remain': 27,
            },
            '2': {
                'send': [],
                'remain': 27,
            },
            '3': {
                'send': [],
                'remain': 27,
            },
        }
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # s榛戞
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # h绾㈡
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # c鏂瑰潡
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # d姊呰姳
        }
        self.play_cards = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
        }
        # 鍓╀綑鐗岀殑绱㈠紩 1020
        self.remain_cards_classbynum = [8] * 13
        self.remain_cards_classbynum.append(2)
        self.remain_cards_classbynum.append(2)
        # end 1020

        self._type = None
        self._stage = None
        self._myPos = None
        self._publicInfo = None
        self._actionList = None
        self._curAction = None
        self._curPos = None
        self._greaterPos = None
        self._greaterAction = None
        self._handCards = None
        self._oppoRank = None
        self._curRank = None
        self._selfRank = None
        self._antiNum = None
        self._antiPos = None
        self._result = None
        self._order = None
        self._curTimes = None
        self._settingTimes = None
        self._victoryNum = None
        self._draws = None
        self._restCards = None
        self.pass_num = 0
        self.my_pass_num = 0

        LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
        DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"

        # TODO: 閫夋墜鍙鏍规嵁(stage, type)鑷琛屽畾涔夊勭悊鐨勫嚱鏁
        self.__parse_func = {
            ("beginning", "notify"): self.notify_begin,
            ("play", "notify"): self.notify_play,
            ("tribute", "notify"): self.notify_tribute,
            ("anti-tribute", "notify"): self.notify_anti,
            ("back", "notify"): self.notify_back,
            ("gameOver", "notify"): self.notify_game_over,
            ("episodeOver", "notify"): self.notify_episode_over,
            ("gameResult", "notify"): self.notify_game_result,

            ("play", "act"): self.act_play,
            ("tribute", "act"): self.act_tribute,
            ("back", "act"): self.act_back,
        }

    def parse(self, msg):
        assert type(msg) == dict
        for key, value in msg.items():
            setattr(self, "_{}".format(key), value)
        try:
            self.__parse_func[(self._stage, self._type)]()
            self._stage = None
            self._type = None
        except KeyError:
            print(msg)
            raise KeyError

    def notify_begin(self):
        """
        娓告垙寮濮嬮樁娈碉紝鍛婄煡姣忎綅鐜╁剁殑鎵嬬墝鎯呭喌
        褰㈠備笅鎵琛ㄧず鐨凧SON:
        {
            "type": "notify",
            "stage": "beginning",
            "handCard": ['S2', 'S2'],
            "myPos": 1,
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        print("游戏开始, 我是{}号位，手牌：{}".format(self._myPos, self._handCards))


    def notify_play(self):
        """
        鍑虹墝闃舵碉紝鐢ㄤ簬閫氱煡鍏朵粬鐜╁跺仛鍑轰簡浠涔堝姩浣
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "notify",
            "stage": "play",
            "curPos": 1,
            "curAction": {"rank": '2', "type": Single, "actions": ['S2']},
            "greaterPos": 1,
            "greaterAction": {"rank": '2', "type": Single, "actions": ['S2']{}
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        if self._curAction[2] != "PASS":
            for card in self._curAction[2]:
                if len(card) >= 2:
                    card_type = str(card[0])
                    self.history[str(self._curPos)]["send"].append(card)
                    self.history[str(self._curPos)]["remain"] -= 1
                    card_value = {"A": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6, "8": 7, "9": 8, "T": 9, "J": 10,
                                  "Q": 11, "K": 12, "R": 13, "B": 13}
                    if card[1] in card_value:
                        x = card_value[card[1]]
                        self.remain_cards[card_type][x] -= 1
        if self._curPos == (self._myPos+2)%4 or self._curPos == self._myPos:
            if self._curAction[0] == "PASS":
                self.pass_num += 1

            else:
                self.pass_num = 0

        if self._curPos == self._myPos:
            if self._curAction[0] == "PASS":
                self.my_pass_num += 1

            else:
                self.my_pass_num = 0


        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        print("{}号位打出{}， 最大动作为{}号位打出的{}".format(self._curPos, self._curAction, self._greaterPos, self._greaterAction), "连续pass数目", self.pass_num)


    def notify_tribute(self):
        """
        杩涜础闃舵碉紝鐢ㄤ簬閫氱煡鎵鏈夌帺瀹惰繘璐¤咃紙浠锛夐兘杩涜础浜嗕粈涔堢墝
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "notify",
            "stage": "tribute",
            "result": [[0, 3, 'S2']] 鎴 [[0, 3, 'S2'], [2, 1, 'S2']]
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        self.tribute_result = self._result
        for tribute_result in self._result:
            tribute_pos, receive_tribute_pos, card = tribute_result

            print("{}号位给{}号位进贡{}".format(tribute_pos, receive_tribute_pos, card))


    def notify_anti(self):
        """
        鎶楄础闃舵碉紝鐢ㄤ簬閫氱煡鎵鏈夌帺瀹讹紝鏈変汉鎶楄础銆傚叾涓璦ntiNums鐨勫彇鍊间笌antiPos鏁扮粍鐨勯暱搴︽墍瀵瑰簲
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "notify",
            "stage": "anti-tribute",
            "antiNums": 2,
            "antiPos": [0, 2]
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        for pos in self._antiPos:
            print("{}号位玩家抗贡".format(pos))

    def notify_back(self):
        """
        杩樿础闃舵碉紝鐢ㄤ簬閫氱煡鎵鏈夌帺瀹惰繕璐¤咃紙浠锛夐兘杩樿础浜嗕粈涔堢墝
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "notify",
            "stage": "back",
            "result": [[3, 0, 'S2']] 鎴 [[3, 0, 'S2'], [1, 2, 'S2']]
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        for back_result in self._result:
            back_pos, receive_back_pos, card = back_result
            print("{}号位给{}号位还贡{}".format(back_pos, receive_back_pos, card))

    def notify_episode_over(self):
        """
        灏忓眬缁撴潫闃舵碉紝鐢ㄤ簬閫氱煡鎵鏈夌帺瀹跺皬灞缁撴潫
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "notify",
            "stage": "episodeOver",
            "order": [0, 1, 2, 3]
            鈥渃urRank": 1,
            "restCards": [[pos, handcards], ...]
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # 閲嶇疆瀛楁
        self.history = {
            '0': {
                'send': [],
                'remain': 27,
            },
            '1': {
                'send': [],
                'remain': 27,
            },
            '2': {
                'send': [],
                'remain': 27,
            },
            '3': {
                'send': [],
                'remain': 27,
            },
        }
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # s榛戞
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # h绾㈡
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # c鏂瑰潡
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # d姊呰姳
        }
        self.play_cards = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
        }
        # 閲嶇疆鍓╀綑鐗岀殑绱㈠紩 1020
        self.remain_cards_classbynum = [8] * 13
        self.remain_cards_classbynum.append(2)
        self.remain_cards_classbynum.append(2)
        # end 1020
        self.pass_num = 0
        self.my_pass_num = 0
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        print("对局结束，完牌次序为{}，结束时所打的等级为{}".format(self._order, self._curRank))
        for rest in self._restCards:
            rest_pos, rest_cards = rest
            print("{}号位剩余卡牌{}".format(rest_pos, rest_cards))

    def notify_game_over(self):
        """
        鍒拌揪鎸囧畾娓告垙娆℃暟娓告垙缁撴潫锛岀敤浜庨氱煡鎵鏈夌帺瀹舵父鎴忕粨鏉
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "notify",
            "stage": "gameOver",
            "curTimes": 1
            鈥渟ettingTimes": 1,
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # 閲嶇疆瀛楁
        self.history = {
            '0': {
                'send': [],
                'remain': 27,
            },
            '1': {
                'send': [],
                'remain': 27,
            },
            '2': {
                'send': [],
                'remain': 27,
            },
            '3': {
                'send': [],
                'remain': 27,
            },
        }
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # s榛戞
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # h绾㈡
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # c鏂瑰潡
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # d姊呰姳
        }
        self.play_cards = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
        }
        # 閲嶇疆鍓╀綑鐗岀殑绱㈠紩 1020
        self.remain_cards_classbynum = [8] * 13
        self.remain_cards_classbynum.append(2)
        self.remain_cards_classbynum.append(2)
        # end 1020
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        print("当前训练次数为{}， 设定的游戏次数为{}".format(self._curTimes, self._settingTimes))

    def notify_game_result(self):
        """
        鍒拌揪鎸囧畾娓告垙娆℃暟娓告垙缁撴潫锛岀敤浜庨氱煡鎵鏈夌帺瀹舵父鎴忕粨鏉
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡銆傝JSON琛ㄧず缁忚繃2鍦哄瑰眬鍚庢父鎴忕粨鏉燂紝鍏朵腑0鍙蜂綅鐜╁跺拰2鍙蜂綅鐜╁惰儨鍒╂℃暟浣2銆
        {
            "type": "notify",
            "stage": "gameResult",
            "victoryNum": [2, 0, 2, 0]
            "draws": [0, 0, 0, 0]
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        print("达到设定场次, 其中0号位胜利{}次，1号位胜利{}次，2号位胜利{}次，3号位胜利{}次".format(*self._victoryNum))
        print("其中平局次数，0号位平局{}次，1号位平局{}次，2号位平局{}次，3号位平局{}次".format(*self._draws))

    def act_play(self):
        """
        鍑虹墝闃舵碉紝鐢ㄤ簬閫氱煡璇ョ帺瀹跺仛鍑哄姩浣
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "act",
            "handCards": [C3, D3, D3, H5, C5, D5, S6, D6 ... ] ,
            "publicInfo": [
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None{}
            ],
            "selfRank": 鈥2鈥,
            "oppoRank": 鈥2鈥,
            "curRank": 鈥2鈥,
            "stage": "play",
            "curPos": -1,
            "curAction": None,
            "greaterAction": -1,
            "greaterPos": None,
            "actionList": {"Single" : {'2': ['S2', 'S2' ...]{} ...{}
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        for i in range(4):
            if self._publicInfo[i]["playArea"] is None:
                self.play_cards[str(i)] = []
            else:
                play_area = self._publicInfo[i]["playArea"]
                # Handle different playArea formats
                if isinstance(play_area, list) and len(play_area) > 2:
                    self.play_cards[str(i)] = play_area[2]
                elif isinstance(play_area, list):
                    self.play_cards[str(i)] = play_area
                else:
                    self.play_cards[str(i)] = []
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        print("我方等级：{}， 对方等级：{}， 当前等级{}".format(self._selfRank, self._oppoRank, self._curRank))
        print("当前动作为{}号-动作{}， 最大动作为{}号-动作{}".format(
            self._curPos, self._curAction, self._greaterPos, self._greaterAction)
        )


    def act_tribute(self):
        """
        杩涜础闃舵碉紝鐢ㄤ簬璇ョ帺瀹惰繘璐
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "act",
            "handCards": [C3, D3, D3, H5, C5, D5, S6, D6 ... ] ,
            "publicInfo": [
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None{}
            ],
            "selfRank": 鈥2鈥,
            "oppoRank": 鈥3鈥,
            "curRank": 鈥3鈥,
            "stage": "tribute",
            "curPos": -1,
            "curAction": None,
            "greaterAction": -1,
            "greaterPos": None,
            "actionList": {"tribute": ["S3"]{}
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # TODO: 选手可自行做出其他处理
        print("我方等级：{}， 对方等级：{}， 当前等级{}".format(self._selfRank, self._oppoRank, self._curRank))
        print("轮到自己进贡，可进贡的牌有: ")

    def act_back(self):
        """
        杩樿础闃舵碉紝鐢ㄤ簬璇ョ帺瀹惰繘璐
        褰㈠備笅鎵琛ㄧず鐨凧SON鏍煎紡:
        {
            "type": "act",
            "handCards": [C3, D3, D3, H5, C5, D5, S6, D6 ... ] ,
            "publicInfo": [
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None{}
            ],
            "selfRank": 鈥3鈥,
            "oppoRank": 鈥2鈥,
            "curRank": 鈥3鈥,
            "stage": "back",
            "curPos": -1,
            "curAction": None,
            "greaterAction": -1,
            "greaterPos": None,
            "actionList": {"back": ["S2", "D3"]{}
        }
        璇蜂粎鍦ㄥ瑰簲鐨凧SON鏍煎紡涓嬭块棶瀵瑰簲鐨勫疄渚嬪睘鎬э紝鑻ユゆ椂璁块棶鍏朵粬灞炴у垯寰堟湁鍙鑳芥槸涔嬪墠澶勭悊鏃舵湭鏇存柊鐨勫疄渚嬪睘鎬э紝涓嶅叿鏈夊噯纭鎬с
        """
        # TODO: 选手可自行做出其他处理
        print("我方等级：{}， 对方等级：{}， 当前等级{}".format(self._selfRank, self._oppoRank, self._curRank))
        print("轮到自己还贡，可还贡的牌有:")

