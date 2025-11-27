# -*- coding: utf-8 -*-
# @Time       : 2020/10/1 19:21
# @Author     : Duofeng Wu
# @File       : gd_handle.py
# @Description: 閼烽崝銊ㄐ掗弸鎰骞栭摂瀣澧嶉崣鎴︿焦娼甸惃鍑SON閺佺増宓

class State(object):

    def __init__(self,name):

        """
        濮ｅ繋閲滅圭偘绶ラ惃鍕绻氶幎銈呯潣閹褍鐟扮安JSON娑撻惃鍕鐡у▓闈涚》绱濈粔浣规箒鐏炵偞褑銆冪粈鐑樼壌閹规稉宥呮倱type閸滃籺age鏉╂稖灞肩瑝閸氬矁袙閺嬫劑
        type:          鐞涖劎銇氬☉鍫熶紖缁璇茬烽妴鍌氬讲閸欐牕鐓庡瘶閹风惢otify閸滃畮ct閵嗕糠otify鐞涖劎銇氶柅姘辩叀缁璇茬烽敍瀹巆t鐞涖劎銇氶崝銊ょ稊缁璇茬烽敍鍫濆祮閺璺哄煂鐠囥儳琚閸ㄥ娈戝☉鍫熶紖閺冨爼娓剁憰浣镐粵閸戝搫濮╂担婊愮礆
        stage:         鐞涖劎銇氬〒鍛婂灆闂冭埖鐐瑰倸褰查崣鏍х厧瀵橀幏鐞eginning, play, tribute, anti-tribute, back, episodeOver, gameOver
                        閸掑棗鍩嗙电懓绨插婵瀣妯佸▓鐐逛礁鍤閻楀矂妯佸▓鐐逛浇绻樼拹锟犳▉濞堢偣浣瑰夌拹锟犳▉濞堢偣浣界箷鐠愶繝妯佸▓鐐逛胶绮ㄩ弶鐔兼▉濞
        myPos:         鐞涖劎銇氶懛瀹歌京娈戞惔褌缍呴崣
        publicInfo:    鐞涖劎銇氬〒鍛婂灆娑撻悳鈺佽泛鍙曢崗鍙樹繆閹
        actionList:    鐞涖劎銇氶崣鐞涘瞼娈戦崝銊ょ稊閸掓勩
        curAction:     鐞涖劎銇氶弻鎰甯虹硅泛浠涢崙铏规畱閸斻劋缍
        curPos:        鐞涖劎銇氶崑姘鍤瑜版挸澧犻崝銊ょ稊閻ㄥ嫮甯虹瑰墎娈戞惔褌缍呴崣
        greaterPos:    鐞涖劎銇氶張婢堆冨З娴ｆ粎娈戦悳鈺佸墎娈戞惔褌缍呴崣
        greaterAction: 鐞涖劎銇氶張婢堆冨煂娴ｇ姴浼愭担
        handCards:     鐞涖劎銇氶幍瀣澧
        oppoRank:      鐞涖劎銇氱佃勫滅粵澶岄獓
        curRank:       鐞涖劎銇氳ぐ鎾冲犲〒鍛婂灆閸︺劋濞囬悽銊ф畱缁涘岄獓None
        selfRank:      鐞涖劎銇氶幋鎴炴煙缁涘岄獓
        antiNum:       鐞涖劎銇氶幎妤勭娴滅儤鏆
        antiPos:       鐞涖劎銇氶幎妤勭閻溾晛璁圭礄娴犻敍澶屾畱 鎼囱傜秴閸
        result:        鐞涖劎銇氭潻娑滅閹存牞鍛扮箷鐠愶紕娈戠紒鎾寸亯
        order:         鐞涖劎銇氱瑰瞼澧濋惃鍕鈥崇碍
        curTimes:      瑜版挸澧犻惃鍕鐟扮湰濞嗏剝鏆
        settingTimes   鐠佹儳鐣鹃惃鍕鐟扮湰濞嗏剝鏆
        victoryNum     鐞涖劎銇氭潏鎯у煂鐠佹儳鐣鹃崷鐑樷剝妞傞惃鍕娓剁紒鍫㈢波閺嬫粣绱欓崫娑撻弬纭呰藉版姘剧礆
        parse_func:    鐞涖劎銇氶悽銊ょ艾鐟欙絾鐎介惃鍕鍤遍弫
        """
        # history = {'0': {'send': [], 'remain': 27}, ...{} 鐠佹澘缍嶉悽銊﹀煕閹垫挸鍤閻ㄥ嫮澧
        # remain_cards = [4 * 14] 鐠佹澘缍嶉悧灞界氨閸撯晙缍戦悧
        # played_cards = {'0': [], ...} 閺堟潪閻銊﹀煕閹垫挸鍤閻ㄥ嫮澧
        # player_id 閻銊﹀煕id
        # current_hands = [] 瑜版挸澧犻幍瀣澧
        # action_list 閸欓幍褑灞藉З娴ｆ粌鍨鐞
        self.tribute_result = None
        self.history = {
            '0': {
                'send': [],
                'remain': 27,
            {},
            '1': {
                'send': [],
                'remain': 27,
            {},
            '2': {
                'send': [],
                'remain': 27,
            {},
            '3': {
                'send': [],
                'remain': 27,
            {},
        {}
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # s姒涙垶
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # h缁俱垺
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # c閺傜懓娼
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # d濮婂懓濮
        {}
        self.play_cards = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
        {}
        # 閸撯晙缍戦悧宀娈戠槐銏犵穿 1020
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

        # TODO: 闁澶嬪滈崣閺嶈勫祦(stage, type)閼风悰灞界暰娑斿婂嫮鎮婇惃鍕鍤遍弫
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
        {}

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
        濞撳憡鍨欏婵瀣妯佸▓纰夌礉閸涘﹦鐓″В蹇庣秴閻溾晛鍓佹畱閹靛澧濋幆鍛鍠
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON:
        {
            "type": "notify",
            "stage": "beginning",
            "handCard": ['S2', 'S2'],
            "myPos": 1,
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        print("濞撳憡鍨欏婵, 閹存垶妲竰{}閸欒渹缍呴敍灞惧滈悧宀嬬窗{}".format(self._myPos, self._handCards))


    def notify_play(self):
        """
        閸戣櫣澧濋梼鑸电夌礉閻銊ょ艾闁姘辩叀閸忔湹绮閻溾晛璺轰粵閸戣桨绨℃禒娑斿牆濮╂担
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "notify",
            "stage": "play",
            "curPos": 1,
            "curAction": {"rank": '2', "type": Single, "actions": ['S2']},
            "greaterPos": 1,
            "greaterAction": {"rank": '2', "type": Single, "actions": ['S2']}
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        if self._curAction[2] != "PASS":
            for card in self._curAction[2]:
                card_type = str(card[0])
                self.history[str(self._curPos)]["send"].append(card)
                self.history[str(self._curPos)]["remain"] -= 1
                card_value = {"A": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6, "8": 7, "9": 8, "T": 9, "J": 10,
                              "Q": 11, "K": 12, "R": 13, "B": 13{}
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


        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        print("{}閸欒渹缍呴幍鎾冲毉{}閿 閺堟径褍濮╂担婊璐焮{}閸欒渹缍呴幍鎾冲毉閻ㄥ墦{}".format(self._curPos, self._curAction, self._greaterPos, self._greaterAction),"鏉╃偟鐢籶ass閺佹壆娲伴敍", self.pass_num)


    def notify_tribute(self):
        """
        鏉╂稖纭闂冭埖纰夌礉閻銊ょ艾闁姘辩叀閹甸張澶屽负鐎规儼绻樼拹陇鍜冪礄娴犻敍澶愬厴鏉╂稖纭娴滃棔绮堟稊鍫㈠
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "notify",
            "stage": "tribute",
            "result": [[0, 3, 'S2']] 閹 [[0, 3, 'S2'], [2, 1, 'S2']]
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        self.tribute_result = self._result
        for tribute_result in self._result:
            tribute_pos, receive_tribute_pos, card = tribute_result

            print("{}閸欒渹缍呴崥鎲憓閸欒渹缍呮潻娑滅{}".format(tribute_pos, receive_tribute_pos, card))


    def notify_anti(self):
        """
        閹舵勭闂冭埖纰夌礉閻銊ょ艾闁姘辩叀閹甸張澶屽负鐎硅圭礉閺堝夋眽閹舵勭閵嗗倸鍙炬稉鐠ntiNums閻ㄥ嫬褰囬崐闂寸瑢antiPos閺佹壆绮嶉惃鍕鏆辨惔锔藉嶇电懓绨
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "notify",
            "stage": "anti-tribute",
            "antiNums": 2,
            "antiPos": [0, 2]
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        for pos in self._antiPos:
            print("{}閸欒渹缍呴悳鈺佽埖濮夌拹".format(pos))

    def notify_back(self):
        """
        鏉╂跨闂冭埖纰夌礉閻銊ょ艾闁姘辩叀閹甸張澶屽负鐎规儼绻曠拹陇鍜冪礄娴犻敍澶愬厴鏉╂跨娴滃棔绮堟稊鍫㈠
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "notify",
            "stage": "back",
            "result": [[3, 0, 'S2']] 閹 [[3, 0, 'S2'], [1, 2, 'S2']]
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        for back_result in self._result:
            back_pos, receive_back_pos, card = back_result
            print("{}閸欒渹缍呴崥鎲憓閸欒渹缍呮潻妯跨{}".format(back_pos, receive_back_pos, card))

    def notify_episode_over(self):
        """
        鐏忓繐鐪缂佹挻娼闂冭埖纰夌礉閻銊ょ艾闁姘辩叀閹甸張澶屽负鐎硅泛鐨鐏炵紒鎾存将
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "notify",
            "stage": "episodeOver",
            "order": [0, 1, 2, 3]
            "curRank": 1,
            "restCards": [[pos, handcards], ...]
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # 闁插秶鐤嗙涙
        self.history = {
            '0': {
                'send': [],
                'remain': 27,
            {},
            '1': {
                'send': [],
                'remain': 27,
            {},
            '2': {
                'send': [],
                'remain': 27,
            {},
            '3': {
                'send': [],
                'remain': 27,
            {},
        {}
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # s姒涙垶
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # h缁俱垺
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # c閺傜懓娼
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # d濮婂懓濮
        {}
        self.play_cards = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
        {}
        # 闁插秶鐤嗛崜鈺缍戦悧宀娈戠槐銏犵穿 1020
        self.remain_cards_classbynum = [8] * 13
        self.remain_cards_classbynum.append(2)
        self.remain_cards_classbynum.append(2)
        # end 1020
        self.pass_num = 0
        self.my_pass_num = 0
        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        print("鐎电懓鐪缂佹挻娼閿涘苯鐣閻楀本鈥崇碍娑撶皶{}閿涘瞼绮ㄩ弶鐔告傞幍閹垫挾娈戠粵澶岄獓娑撶皶{}".format(self._order, self._curRank))
        for rest in self._restCards:
            rest_pos, rest_cards = rest
            print("{}閸欒渹缍呴崜鈺缍戦崡锛勫漿{}".format(rest_pos, rest_cards))

    def notify_game_over(self):
        """
        閸掓媽鎻閹稿洤鐣惧〒鍛婂灆濞嗏剝鏆熷〒鍛婂灆缂佹挻娼閿涘瞼鏁ゆ禍搴ㄦ氨鐓￠幍閺堝屽负鐎硅埖鐖堕幋蹇曠波閺
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "notify",
            "stage": "gameOver",
            "curTimes": 1
            "settingTimes": 1,
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # 闁插秶鐤嗙涙
        self.history = {
            '0': {
                'send': [],
                'remain': 27,
            {},
            '1': {
                'send': [],
                'remain': 27,
            {},
            '2': {
                'send': [],
                'remain': 27,
            {},
            '3': {
                'send': [],
                'remain': 27,
            {},
        {}
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # s姒涙垶
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # h缁俱垺
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # c閺傜懓娼
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # d濮婂懓濮
        {}
        self.play_cards = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
        {}
        # 闁插秶鐤嗛崜鈺缍戦悧宀娈戠槐銏犵穿 1020
        self.remain_cards_classbynum = [8] * 13
        self.remain_cards_classbynum.append(2)
        self.remain_cards_classbynum.append(2)
        # end 1020
        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        print("瑜版挸澧犵拋缂佸啯鈩冩殶娑撶皶{}, 鐠佹儳鐣鹃惃鍕鐖堕幋蹇斺剝鏆熸稉绨晑".format(self._curTimes, self._settingTimes))

    def notify_game_result(self):
        """
        閸掓媽鎻閹稿洤鐣惧〒鍛婂灆濞嗏剝鏆熷〒鍛婂灆缂佹挻娼閿涘瞼鏁ゆ禍搴ㄦ氨鐓￠幍閺堝屽负鐎硅埖鐖堕幋蹇曠波閺
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱￠妴鍌滼SON鐞涖劎銇氱紒蹇氱箖2閸﹀搫鐟扮湰閸氬孩鐖堕幋蹇曠波閺夌噦绱濋崗鏈佃厬0閸欒渹缍呴悳鈺佽泛鎷2閸欒渹缍呴悳鈺佹儼鍎ㄩ崚鈺傗剝鏆熸担2閵
        {
            "type": "notify",
            "stage": "gameResult",
            "victoryNum": [2, 0, 2, 0]
            "draws": [0, 0, 0, 0]
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        print("鏉堟儳鍩岀拋鎯х暰閸︾儤, 閸忔湹鑵0閸欒渹缍呴懗婊冨焺{}濞嗏槄绱1閸欒渹缍呴懗婊冨焺{}濞嗏槄绱2閸欒渹缍呴懗婊冨焺{}濞嗏槄绱3閸欒渹缍呴懗婊冨焺{}濞".format(*self._victoryNum))
        print("閸忔湹鑵戦獮鍐茬湰濞嗏剝鏆熼敍0閸欒渹缍呴獮鍐茬湰{}濞嗏槄绱1閸欒渹缍呴獮鍐茬湰{}濞嗏槄绱2閸欒渹缍呴獮鍐茬湰{}濞嗏槄绱3閸欒渹缍呴獮鍐茬湰{}濞".format(*self._draws))

    def act_play(self):
        """
        閸戣櫣澧濋梼鑸电夌礉閻銊ょ艾闁姘辩叀鐠囥儳甯虹硅泛浠涢崙鍝勫З娴
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "act",
            "handCards": [C3, D3, D3, H5, C5, D5, S6, D6 ... ] ,
            "publicInfo": [
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None}
            ],
            "selfRank": '2',
            "oppoRank": '2',
            "curRank": '2',
            "stage": "play",
            "curPos": -1,
            "curAction": None,
            "greaterAction": -1,
            "greaterPos": None,
            "actionList": {"Single" : {'2': ['S2', 'S2' ...]} ...{}
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        for i in range(4):
            if self._publicInfo[i]["playArea"] is None:
                self.play_cards[str(i)] = []
            else:
                self.play_cards[str(i)] = self._publicInfo[i]["playArea"][2]
        # TODO: 闁澶嬪滈崣閼风悰灞戒粵閸戝搫鍙炬禒鏍у嫮鎮
        print("鎴戞柟绛夌骇锛歿{}锛 瀵规柟绛夌骇锛歿{}锛 褰撳墠绛夌骇{}".format(self._selfRank, self._oppoRank, self._curRank))
        print("褰撳墠鍔ㄤ綔涓簕{}鍙-鍔ㄤ綔{}锛 鏈澶у姩浣滀负{}鍙-鍔ㄤ綔{}".format(
            self._curPos, self._curAction, self._greaterPos, self._greaterAction)
        )


    def act_tribute(self):
        """
        鏉╂稖纭闂冭埖纰夌礉閻銊ょ艾鐠囥儳甯虹规儼绻樼拹
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "act",
            "handCards": [C3, D3, D3, H5, C5, D5, S6, D6 ... ] ,
            "publicInfo": [
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None}
            ],
            "selfRank": '2',
            "oppoRank": '3',
            "curRank": '3',
            "stage": "tribute",
            "curPos": -1,
            "curAction": None,
            "greaterAction": -1,
            "greaterPos": None,
            "actionList": {"tribute": ["S3"]}
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        print("鎴戞柟绛夌骇锛歿{}锛 瀵规柟绛夌骇锛歿{}锛 褰撳墠绛夌骇{}".format(self._selfRank, self._oppoRank, self._curRank))
        print("杞鍒拌嚜宸辫繘璐★紝鍙杩涜础鐨勭墝鏈: ")

    def act_back(self):
        """
        鏉╂跨闂冭埖纰夌礉閻銊ょ艾鐠囥儳甯虹规儼绻樼拹
        瑜般垹鍌欑瑓閹电悰銊с仛閻ㄥ嚙SON閺嶇厧绱:
        {
            "type": "act",
            "handCards": [C3, D3, D3, H5, C5, D5, S6, D6 ... ] ,
            "publicInfo": [
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None},
                {'rest': 27, 'playArea': None}
            ],
            "selfRank": '3',
            "oppoRank": '2',
            "curRank": '3',
            "stage": "back",
            "curPos": -1,
            "curAction": None,
            "greaterAction": -1,
            "greaterPos": None,
            "actionList": {"back": ["S2", "D3"]}
        {}
        鐠囪渹绮庨崷銊ョ懓绨查惃鍑SON閺嶇厧绱℃稉瀣鍧楁６鐎电懓绨查惃鍕鐤勬笟瀣鐫橀幀褝绱濋懟銉︺倖妞傜拋鍧楁６閸忔湹绮鐏炵偞褍鍨瀵板牊婀侀崣閼宠姤妲告稊瀣澧犳径鍕鎮婇弮鑸垫弓閺囧瓨鏌婇惃鍕鐤勬笟瀣鐫橀幀褝绱濇稉宥呭徔閺堝婂櫙绾閹褋
        """
        # TODO: 閫夋墜鍙鑷琛屽仛鍑哄叾浠栧勭悊
        print("鎴戞柟绛夌骇锛歿{}锛 瀵规柟绛夌骇锛歿{}锛 褰撳墠绛夌骇{}".format(self._selfRank, self._oppoRank, self._curRank))
        print("杞鍒拌嚜宸辫繕璐★紝鍙杩樿础鐨勭墝鏈:")
