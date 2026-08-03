import os
import random
import sys
import json
import numpy as np
from collections import Counter

cardscale = ['A','2','3','4','5','6','7','8','9','0','J','Q','K']
suitset = ['h','d','s','c']
jokers = ['jo', 'jO']
pointorder = ['2','3','4','5','6','7','8','9','0','J','Q','K','A']
Normaltypes = ("single", "pair", "three", "straight", "set", "three_straight", "triple_pairs")
scaletypes = ("straight", "three_straight", "triple_pairs")
errored = [None for i in range(4)]
printed = False
###################################################牌型编码###################################################
# 红桃 方块 黑桃 草花
# 3 4 5 6 7 8 9 10 J Q K A 2 joker & Joker
# (0-hA 1-dA 2-sA 3-cA) (4-h2 5-d2 6-s2 7-c2) …… 52-joker 53-Joker
# 请注意：10记为0
# 共2副108张
###################################################牌型编码###################################################
def num2Poker(num): # num: int-[0,107]
    # Already a poker
    if type(num) is str and (num in jokers or (num[0] in suitset and num[1] in cardscale)):
        return num
    # Locate in 1 single deck
    NumInDeck = num % 54
    # joker and Joker:
    if NumInDeck == 52:
        return "jo"
    if NumInDeck == 53:
        return "jO"
    # Normal cards:
    pokernumber = cardscale[NumInDeck // 4]
    pokersuit = suitset[NumInDeck % 4]
    return pokersuit + pokernumber

def Poker2Num(poker, deck): # poker: str
    NumInDeck = -1
    if poker[1] == "o":
        NumInDeck = 52
    elif poker[1] == "O":
        NumInDeck = 53
    else:
        NumInDeck = cardscale.index(poker[1])*4 + suitset.index(poker[0])
    if NumInDeck in deck:
        return NumInDeck
    else:
        return NumInDeck + 54

# checking the consistency between action and claim
def isLegalClaim(action: list, claim: list, level: str, currplayer: int):
    covering = "h" + level
    if len(action) != len(claim):
        setError(currplayer, "ILLEGAL_CLAIM")
    action_pok = [num2Poker(p) for p in action]
    claim_pok = [num2Poker(p) for p in claim]
    for pok in action_pok:
        if pok != covering:
            if pok in claim_pok:
                claim_pok.remove(pok)
            else:
                setError(currplayer, "ILLEGAL_CLAIM")
    for pok in claim_pok:
        if pok[1] == 'o' or pok[1] == 'O':
            setError(currplayer, "ILLEGAL_CLAIM")
    return True

# returning: pokertype, covering: int, points
def checkPokerType(poker: list):
    if poker == []:
        return "pass", ()
    # covering = "h" + level
    poker = [num2Poker(p) for p in poker]
    if len(poker) == 1:
        return "single", (poker[0][1])
    if len(poker) == 2:
        if poker[0][1] == poker[1][1]:
            if poker[0][0] == 'j': # Jokers
                if poker[0] == poker[1]:
                    return "pair", (poker[0][1]) # 大小王用"jo""jO"区分
                else: return "invalid", ()
            else: return "pair", (poker[0][1])
    points = [p[1] for p in poker]
    cnt = Counter(points)
    vals = list(cnt.values())
    if len(poker) == 3:
        if "o" in points or "O" in points: 
            return "invalid", ()
        if vals.count(3) == 1:
            return "three", (points[0])
    if len(poker) == 4: # should be a bomb
        if "o" in points or "O" in points: # should be a rocket
            if cnt["o"] == 2 and cnt["O"] == 2:
                return "rocket", ("jo")
            else:
                return "invalid", ()
        if vals.count(4) == 1:
            return "bomb", (4, points[0])
    if len(poker) == 5: # could be straight, straight flush, three&two or bomb
        if vals.count(5) == 1:
            return "bomb", (5, points[0])
        if vals.count(3) == 1:
            if vals.count(2) == 1: # set: 三带二 or bomb with 2 coverings
                three = ''
                two = ''
                for k in list(cnt.keys()):
                    if cnt[k] == 3:
                        three = k
                    elif cnt[k] == 2:
                        two = k
                return "set", (three, two)
            return "invalid", ()
        if vals.count(1) >= 4: # should be straight
            points.sort(key=lambda x: cardscale.index(x))
            suits = [p[0] for p in poker]
            suit_cnt = Counter(suits)
            suit_vals = list(suit_cnt.values())
            flush = False
            if suit_vals.count(5) == 1:
                flush = True
            first = points[0]
            if first == 'A':
                if points == ['A', '0', 'J', 'Q', 'K']:
                    if flush:
                        return "straight_flush", ('0')
                    return "straight", ('0')
            sup_straight = [cardscale[cardscale.index(first)+i] for i in range(5)]
            if points == sup_straight:
                if flush:
                    return "straight_flush", (first)
                return "straight", (first)
        return "invalid", ()
    if len(poker) == 6: # could be triple_pairs, three_straight, bomb
        if vals.count(6) == 1:
            return "bomb", (6, points[0])
        if vals.count(3) == 2:
            ks = []
            for k in list(cnt.keys()):
                ks.append(k)
            ks.sort(key=lambda x: cardscale.index(x))
            if 'A' in ks:
                if ks == ['A', '2']:
                    return "three_straight", ('A')
                if ks == ['A', 'K']:
                    return "three_straight", ('K')
                return "invalid", ()
            if cardscale.index(ks[1]) - cardscale.index(ks[0]) == 1:
                return "three_straight", (ks[0])
            return "invalid", ()
        if vals.count(2) == 3:
            ks = []
            for k in list(cnt.keys()):
                ks.append(k)
            ks.sort(key=lambda x: cardscale.index(x))
            if 'A' in ks:
                if ks == ['A', 'Q', 'K']:
                    return "triple_pairs", ('Q')
                if ks == ['A', '2', '3']:
                    return "triple_pairs", ('A')
                return "invalid", ()
            pairs = [cardscale[cardscale.index(ks[0])+i] for i in range(3)]
            if ks == pairs:
                return "triple_pairs", (ks[0])
            return "invalid", ()
        
        return "invalid", ()
    if len(poker) > 6 and len(poker) <= 10:
        if vals.count(len(poker)) == 1:
            bomb = points[0]
            return "bomb", (len(poker), bomb)
    return "invalid", ()

def initGame(full_input):
    seedRandom = str(random.randint(0, 2147483647))

    if "initdata" not in full_input:
        full_input["initdata"] = {}
    try:
        full_input["initdata"] = json.loads(full_input["initdata"])
    except Exception:
        pass
    if type(full_input["initdata"]) is not dict:
        full_input["initdata"] = {}

    if "seed" in full_input["initdata"]:
        seedRandom = full_input["initdata"]["seed"] 
    
    random.seed(seedRandom)
    if "allocation" in full_input["initdata"]:
        allocation = full_input["initdata"]["allocation"]
    else: # 产生大家各自有什么牌
        allo = [i for i in range(108)]
        random.shuffle(allo)
        allocation = [allo[:27], allo[27:54], allo[54:81], allo[81:108]]

    
    return full_input, seedRandom, allocation
        
def setError(player, reason): # player: int-[0,3] reason: str
    global printed
    if player == -1:
        raise ValueError("SYSTEM_ERROR")
    if errored[player] is None:
        errored[player] = reason
    endingScores = {}
    for i in range(4):
        if i == player:
            endingScores[str(i)] = -2 # error punishment
        elif i == (player + 2) % 4:
            endingScores[str(i)] = 0
        else:
            endingScores[str(i)] = 1

    print(json.dumps({
        "command": "finish",
        "content": endingScores,
        "display": {
            "currplayer": player,
            "score": endingScores,
            "error": errored
        }
    }))
    printed = True
    exit(0)

def checkBigger(pokertype1, points1, pokertype2, points2): # return True if pokertype2 is bigger than pokertype1
                                         # report an error if pokertype2 mismatches pokertype1 
    if pokertype2 == "rocket":
        return True
    if pokertype1 == "rocket":
        return False
    
    if pokertype1 in Normaltypes:
        if pokertype2 in Normaltypes:
            if pokertype1 == pokertype2:
                if pokertype1 in scaletypes and cardscale.index(points2[0]) > cardscale.index(points1[0]):
                    return True
                if pokertype1 not in scaletypes and pointorder.index(points2[0]) > pointorder.index(points1[0]):
                    return True
                return False
            return "error"
        return True
    if pokertype2 in Normaltypes:
        return "error"
    if pokertype1 == "bomb":
        if pokertype2 == "bomb":
            if points2[0] == points1[0] and pointorder.index(points2[1]) > pointorder.index(points1[1]):
                return True
            if points2[0] > points1[0]:
                return True
            return False
        if pokertype2 == "straight_flush":
            if points1[0] < 6:
                return True
            return False
        return False
    if pokertype1 == "straight_flush":
        if pokertype2 == "bomb":
            if points2[0] >= 6:
                return True
            return False
        if pokertype2 == "straight_flush":
            if cardscale.index(points2[0]) > cardscale.index(points1[0]):
                return True
            return False
        return False
    return False

def isValidTribute(allo: list, poker: int, level: str, currplayer: int):
    # allo: deck of the player
    if poker not in allo:
        setError(currplayer, "NOT_YOUR_POKER")
    deck = [num2Poker(p) for p in allo]
    poker = num2Poker(poker)
    if "jO" in deck:
        if poker != "jO":
            setError(currplayer, "INVALID_MOVE")
        return True
    elif "jo" in deck:
        if poker != "jo":
            setError(currplayer, "INVALID_MOVE")
        return True
    else:
        covering = "h" + level
        points = [p[1] for p in deck]
        point_alldiff = list(set(points))
        if level in points:
            if covering not in deck:
                if poker[1] != level:
                    setError(currplayer, "INVALID_MOVE")
                return True
            with_level = [p for p in deck if p[1] == level] # make sure there's no other levels
            level_suit = [p[0] for p in with_level]
            if 'd' in level_suit or 's' in level_suit or 'c' in level_suit:
                if poker[1] != level:
                    setError(currplayer, "INVALID_MOVE")
                return True
            point_alldiff.remove(level)
        point_alldiff.sort(key=lambda x: pointorder.index(x), reverse=True)
        if poker[1] != point_alldiff[0]:
            setError(currplayer, "INVALID_MOVE")
        return True      

def isValidReturn(allo: list, poker: int, level: str, currplayer: int):
    if poker not in allo:
        setError(currplayer, "NOT_YOUR_POKER")
    poker = num2Poker(poker)
    if level == '9':
        if pointorder.index(poker[1]) > pointorder.index('8'):
            setError(currplayer, "INVALID_MOVE")
        return True
    if pointorder.index(poker[1]) > pointorder.index('9'):
        setError(currplayer, "INVALID_MOVE")
    return True

def settle(done, finalpok):
    global printed
    playerlist = [0, 1, 2, 3]
    currplayer = done[-1]
    result_ranking = done
    for i in playerlist:
        if i not in result_ranking:
            result_ranking.append(i)
    if (result_ranking[0] - result_ranking[1]) % 2 == 0: #
        score = 3
    elif (result_ranking[0] - result_ranking[2]) % 2 == 0: #
        score = 2
    else:
        score = 1
    endingScores = {}
    for i in range(4):
        if (i - result_ranking[0]) % 2 == 0:
            endingScores[str(i)] = score
        else:
            endingScores[str(i)] = 0
    print(json.dumps({
        "command": "finish",
        "content": endingScores,
        "display": {
            "event": {
                "currplayer": currplayer,
                "action": "play",
                "poker": finalpok
            },
            "score": endingScores
        }
    }))
    printed = True
    exit(0)

def set_level(level):
    global pointorder
    # pointorder is a global variable
    pointorder.remove(level)
    pointorder.append(level)
    pointorder.extend(["o", "O"])
    
def recover_state(full_input):
    '''
    Recovering current gamestate (In play stage)
    '''
    lenLog = len(full_input["log"])
    allocation = full_input["initdata"]["allocation"]
    initdata = full_input["initdata"]
    tribute = initdata["tribute"]
    first = initdata["first"]
    last = initdata["last"]
    globalInfo = list(full_input["log"][-2]["output"]["content"].values())[0]["global"]
    level = globalInfo["level"]
    set_level(level)
    resist = globalInfo["resist"]
    tribute_cards_list = list(globalInfo["tribute_cards"].values())
    return_cards_list = list(globalInfo["return_cards"].values())
    
    if not resist: # clearing tributes and returns
        if tribute == 2: # double tribute
            if pointorder.index(num2Poker(tribute_cards_list[0])[1]) ==  pointorder.index(num2Poker(tribute_cards_list[1])[1]): # same, pick clockwise
                for player in (first, (first+2)%4):
                    player_tribute = globalInfo["tribute_cards"][str((player+1)%4)]
                    player_recept = (player+1) % 4
                    player_return = globalInfo["return_cards"][str(player)]
                    allocation[player].append(player_tribute)
                    allocation[player_recept].remove(player_tribute)
                    allocation[player_recept].append(player_return)
                    allocation[player].remove(player_return)
            else:
                tribute_list = list(globalInfo["tribute_cards"].items())
                tribute_list.sort(key=lambda x: pointorder.index(num2Poker(x[1])[1]), reverse=True)
                for player, tribute in zip((first, (first+2)%4), tribute_list):
                    player_return = globalInfo["return_cards"][str(player)]
                    allocation[player].append(tribute[1])
                    allocation[int(tribute[0])].remove(tribute[1])
                    allocation[int(tribute[0])].append(player_return)
                    allocation[player].remove(player_return)
        elif tribute == 1:
            _tribute = globalInfo["tribute_cards"][str(last)]
            _return = globalInfo["return_cards"][str(first)]
            allocation[first].append(_tribute)
            allocation[last].remove(_tribute)
            allocation[last].append(_return)
            allocation[first].remove(_return)
    
    for turn_id in range(0, lenLog-2, 2):
        p_request = full_input["log"][turn_id]
        gamestage = list(p_request["output"]["content"].values())[0]["stage"]
        if gamestage == "play":
            p_response = full_input["log"][turn_id+1]
            player = int(list(p_response.keys())[0])
            move = p_response[str(player)]["response"]
            if move != []:
                for pok in move[0]:
                    allocation[player].remove(pok)
    
    return allocation

    
def solve_tribute(full_input): 
    '''
    Solving tribute/return stages
    Entering this function when: 
        "tribute": True
        "resist" in globalInfo
        "stage": "tribute"/"return"
    '''
    global currplayer
    last_res = full_input["log"][-1]
    last_req = full_input["log"][-2]
    stage = list(last_req["output"]["content"].values())[0]["stage"]
    currplayer = int(list(last_res.keys())[0])
    response = last_res[str(currplayer)]["response"]
    allocation = full_input["initdata"]["allocation"]
    initdata = full_input["initdata"]
    tribute = initdata["tribute"]
    first = initdata["first"]
    globalInfo = list(full_input["log"][-2]["output"]["content"].values())[0]["global"]
    level = globalInfo["level"]
    set_level(level)
    resist = globalInfo["resist"]
    
    if type(response) is not list: 
        setError(currplayer, "INVALID_FORMAT")
    if resist:
        pok = -1
        if len(response) != 0:
            setError(currplayer, "INVALID_MOVE")
        if stage == "tribute":
            globalInfo["tribute_cards"][str(currplayer)] = -1
        elif stage == "return":
            globalInfo["return_cards"][str(currplayer)] = -1
    else:
        if len(response) != 1:
            setError(currplayer, "INVALID_MOVE")
        if stage == "tribute":
            if isValidTribute(allocation[currplayer], response[0], level, currplayer):
                globalInfo["tribute_cards"][str(currplayer)] = response[0]
        elif stage == "return":
            if isValidReturn(allocation[currplayer], response[0], level, currplayer):  
                globalInfo["return_cards"][str(currplayer)] = response[0]
        pok = response[0]
    tribute_cards_list = list(globalInfo["tribute_cards"].values())
    return_cards_list = list(globalInfo["return_cards"].values())
    printContent = {}
    printContent["global"] = globalInfo
    if len(tribute_cards_list) < tribute: # Need tributing
        printContent["stage"] = "tribute"
        nextplayer = (currplayer + 2) % 4
    elif len(return_cards_list) == 0: # First to return
        printContent["stage"] = "return"
        nextplayer = first
    elif len(return_cards_list) < tribute: # Need second returning
        printContent["stage"] = "return"
        nextplayer = (first + 2) % 4
    else: # start playing
        if not resist:
            if tribute == 2:
                tribute_cards_list = list(globalInfo["tribute_cards"].values())
                if pointorder.index(num2Poker(tribute_cards_list[0])[1]) ==  pointorder.index(num2Poker(tribute_cards_list[1])[1]): # same, pick clockwise
                    recept = (currplayer+1) % 4
                elif pointorder.index(num2Poker(tribute_cards_list[0])[1]) >  pointorder.index(num2Poker(tribute_cards_list[1])[1]):
                    recept = int(list(globalInfo["tribute_cards"].keys())[1])
                else:
                    recept = int(list(globalInfo["tribute_cards"].keys())[0])
            else:
                recept = int(list(globalInfo["tribute_cards"].keys())[0])
            nextplayer = (recept + 2) % 4
        else:
            nextplayer = globalInfo["first"]
        printContent["stage"] = "play"
        printContent["history"] = [{}, {}, {}, {}]
        printContent["done"] = []
        printContent["pass_on"] = -1
    printAll = {
        "command": "request",
        "content": {
            str(nextplayer): printContent
        },
        "display": {
            "event": {
                "currplayer": currplayer,
                "action": stage,
                "poker": pok
            },
            "resist": resist
        }
    }
    print(json.dumps(printAll))
    return

def solve_play(full_input):
    global currplayer
    allocation = recover_state(full_input)
    globalInfo = list(full_input["log"][-2]["output"]["content"].values())[0]["global"]
    latest_request = full_input["log"][-2]
    last_res = full_input["log"][-1]
    currplayer = int(list(last_res.keys())[0])
    response = last_res[str(currplayer)]["response"]
    history = list(latest_request["output"]["content"].values())[0]["history"]
    if "done" in list(full_input["log"][-2]["output"]["content"].values())[0]:
        done = list(full_input["log"][-2]["output"]["content"].values())[0]["done"]
    else: done = []
    if "pass_on" in list(full_input["log"][-2]["output"]["content"].values())[0]:
        pass_on = list(full_input["log"][-2]["output"]["content"].values())[0]["pass_on"]
    globalInfo = list(full_input["log"][-2]["output"]["content"].values())[0]["global"]
    level = globalInfo["level"]         
    this_done = 0
    lastRes = None
    for hsres in history:
        if "response" in hsres and hsres["response"][0] != []:
            lastRes = hsres
    if not lastRes:
        lastAction = []
        lastClaim = []
    else:
        lastAction = lastRes["response"][0]
        lastClaim = lastRes["response"][1]
    if response == []:
        action = []
        claim = []
    else:
        action = response[0]
        claim = response[1]
    if isLegalClaim(action, claim, level, currplayer):
        cur_pokertype, cur_points = checkPokerType(claim)
    #covering_num is no longer usable in the new version
    if cur_pokertype == "invalid":
        setError(currplayer, "INVALID_TYPE")
    won = True
    onpass = False
    nextplayer = (currplayer+1) % 4
    for move in history[::-1]:
        if "player" in move and move["player"] == currplayer:
            break
        if "response" in move and len(move["response"][0]) > 0:
            won = False
            break
    if action == []: 
        if won: # lead
            setError(currplayer, "INVALID_PASS")
    else: 
        if pass_on != -1: # pass_on solved immediately
            this_done += 1
            pass_on = -1
        if not won: # not the lead
            last_pokertype, last_points = checkPokerType(lastClaim)
            bigger = checkBigger(last_pokertype, last_points, cur_pokertype, cur_points)
            if bigger == "error":
                setError(currplayer, "POKERTYPE_MISMATCH")
            if not bigger:
                setError(currplayer, "SMALLER_POINTS")
        
    new_history = history[1:]
    response_move = {
        "player": currplayer,
        "response": [action, claim]
    }
    new_history.append(response_move)
    
    for poker in action:
        allocation[currplayer].remove(poker)
    if len(allocation[currplayer]) == 0: # finishing in current move
        pass_on = currplayer 
        done.append(currplayer)
        if len(done) == 3 or (len(done)==2 and (done[1]-done[0]) % 2 == 0): # finishing the game
            finalpok = {
                "poker": response,
                "type": cur_pokertype,
                "points": cur_points
            }
            settle(done, finalpok)
    
    nextplayer = (currplayer+1) % 4
    while nextplayer in done:
        if pass_on == nextplayer:
            this_done += 1
            onpass = True
            silence = True
            for move in history[::-1]:
                if move["player"] == pass_on:
                    break
                if len(move["response"][0]) > 0:
                    silence = False
                    break
            if silence and onpass:
                nextplayer = (pass_on + 2) % 4
            pass_on = -1
        else:
            nextplayer = (nextplayer+1) % 4 
    printContent = {}  
    printContent["stage"] = "play"
    printContent["history"] = new_history
    printContent["done"] = done
    printContent["pass_on"] = pass_on
    printContent["global"] = globalInfo
    printAll = {
        "command": "request",
        "content": {
            str(nextplayer): printContent
        },
        "display": {
            "event": {
                "currplayer": currplayer,
                "action": "play",
                "poker": {
                    "poker": response,
                    "type": cur_pokertype,
                    "points": cur_points
                }
            },
            "player": nextplayer
        }
    }
    if this_done:
        printAll["display"]["new_done"] = this_done
    print(json.dumps(printAll))
    return

def solve_init(full_input):
    printContent = {}
    globalInfo = {}
    curr_alloc = [[], [], [], []]
    full_input, seedRandom, allocation = initGame(full_input)
    initdata = {}
    initdata["allocation"] = allocation
    initdata["seed"] = seedRandom
    if "level" not in full_input["initdata"]:
        initdata["level"] = ["2", "2"]
    else:
        initdata["level"] = full_input["initdata"]["level"]
    if "tribute" not in full_input["initdata"] or full_input["initdata"]["tribute"] == 0:
        initdata["tribute"] = 0
        initdata["first"] = None
        initdata["last"] = None
    else:
        initdata["tribute"] = full_input["initdata"]["tribute"]
        if "first" not in full_input["initdata"] or "last" not in full_input["initdata"]:
            initdata["tribute"] = 0
            initdata["first"] = None
            initdata["last"] = None
        elif full_input["initdata"]["tribute"] == 2 and (full_input["initdata"]["first"] - full_input["initdata"]["last"]) % 2 == 0: # 初始化出错，回退为不进贡情形
            initdata["tribute"] = 0
            initdata["first"] = None
            initdata["last"] = None
        else:
            initdata["first"] = full_input["initdata"]["first"]
            initdata["last"] = full_input["initdata"]["last"]
    if initdata["tribute"]:
        globalInfo["level"] = initdata["level"][initdata["first"]%2]
    else:
        globalInfo["level"] = initdata["level"][0]
    level = globalInfo["level"]
    set_level(level)
    globalInfo["tribute"] = initdata["tribute"]
    globalInfo["first"] = initdata["first"]
    globalInfo["last"] = initdata["last"]

    printContent["stage"] = "deal"
    printContent["deliver"] = allocation[0]
    curr_alloc[0] = allocation[0]
    printContent["your_id"] = 0
    printContent["global"] = globalInfo

    print(json.dumps({
        "command": "request",
        "content": {
            "0": printContent
        },
        "display": {
            "event": {
                "currplayer": -1,
                "action": "init"
            },
            "allocation": allocation,  
            "level": globalInfo["level"],
            "first": globalInfo["first"],
            "last": globalInfo["last"],
            "tribute": globalInfo["tribute"]
        },
        "initdata": initdata
    }))
    return

def solve_deliver(full_input):
    printContent = {}
    lenLog = len(full_input["log"])
    curr_alloc = [[], [], [], []]
    global currplayer
    for i in range(lenLog):
        if i % 2 == 0:
            turnlog = full_input["log"][i]
            player = int(list(turnlog["output"]["content"].keys())[0])
            curr_alloc[player] = turnlog["output"]["content"][str(player)]["deliver"]

    raw_response = full_input["log"][-1]
    currplayer = int(list(raw_response.keys())[0])
    response = raw_response[str(currplayer)]["response"]
    globalInfo = list(full_input["log"][-2]["output"]["content"].values())[0]["global"]
    if type(response) is not list:
        setError(currplayer, "INVALID_FORMAT")
    if len(response) > 0:
        setError(currplayer, "INVALID_MOVE")
    if lenLog < 8:
        nextplayer = (currplayer + 1) % 4
        allocation = full_input["initdata"]["allocation"]
        printContent["stage"] = "deal"
        printContent["deliver"] = allocation[nextplayer]
        printContent["global"] = globalInfo
        printContent["your_id"] = nextplayer
        printAll = {
            "command": "request",
            "content": {
                str(nextplayer): printContent
            },
            "display": {
                "event": {
                    "currplayer": currplayer,
                    "action": "deal"
                }
            }
        }
        print(json.dumps(printAll))

    elif lenLog == 8: # 进贡第一回合
        resist = False
        tribute = globalInfo["tribute"]
        printContent["stage"] = "tribute"
        globalInfo["tribute_cards"] = {}
        globalInfo["return_cards"] = {}
        printContent["global"] = globalInfo
        first = globalInfo["first"]
        last = globalInfo["last"]
        allocation = full_input["initdata"]["allocation"]
        if tribute: 
            if tribute == 2: 
                sum_deck = allocation[last] + allocation[(last+2)%4]
                if 53 in sum_deck and 107 in sum_deck:
                    resist = True
            else:
                if 53 in allocation[last] and 107 in allocation[last]:
                    resist = True
            nextplayer = last
            globalInfo["resist"] = resist
            printAll = {
                "command": "request",
                "content": {
                    str(nextplayer): printContent
                },
                "display": {
                    "event": {
                        "currplayer": currplayer,
                        "action": "deal",
                    },
                    "resist": resist
                }
            }
        else:
            nextplayer = 0
            resist = False
            globalInfo["resist"] = resist
            printContent["stage"] = "play"
            printContent["history"] = [[], [], [], []]
            printContent["done"] = []
            printContent["pass_on"] = -1
            printAll = {
                "command": "request",
                "content": {
                    str(nextplayer): printContent
                },
                "display": {
                    "event": {
                        "currplayer": currplayer,
                        "action": "deal"
                    },
                    "tribute": -1
                }
            }
        print(json.dumps(printAll))
    return


def main(full_input):
    global currplayer
    currplayer = -1
    try:
        lenLog = len(full_input["log"])
        if lenLog == 0:
            solve_init(full_input)
        elif lenLog <= 8:
            solve_deliver(full_input)
        else:
            last_req = full_input["log"][-2]
            stage = list(last_req["output"]["content"].values())[0]["stage"]
            if stage in ["tribute", "return"]:
                solve_tribute(full_input)
            elif stage == "play":
                solve_play(full_input)
    except:
        if not printed:
            setError(currplayer, "UNKNOWN_ERROR")
        
_online = os.environ.get("USER", "") == "root" 
printed = False
currplayer = -1      
if __name__ == '__main__':
    if _online:
        full_input = json.loads(input())
    else:
        with open("test.json") as fo:
            full_input = json.load(fo)
    main(full_input)