import json
import pytz
import uvicorn

from utils import msg
from typing import Dict
from pprint import pprint
from prisma import Prisma
from fastapi import FastAPI
from typing import List, Union
from datetime import datetime
from llama_vision import perform_ocr
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
db = Prisma(auto_register=True)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Flags
# 👷🏻‍♂️ ING
# 🧪 TEST
# 🏷️ DONE


# 🏷️ DONE
############### 상품 등록 ###################
# req로 받아온 item_name, price를 받아서      #
# item 테이블에 저장                         #
###########################################
@app.post("/addItem")
async def addItem(req: Dict):
    await db.connect()
    try:
        info = req['action']['params']['item_info']
        itemData = info.split(',')

        for item in itemData:
            # '-'으로 item을 나누고 그 안에서 0번째(index 0)는 name,
            # 1번쨰(index 1)는 price로 저장. 둘 다 공백 제거
            name, price = item.split('-')
            name = name.strip()
            price = price.strip().replace("원", "")  # '원' 문자 제거

            # 해당하는 이름과 같은 이름의 상품이 있는지 확인
            existing_item = await db.item.find_first(
                where={
                    "name": name,
                },
            )
            if existing_item:
                return msg("🌿 이미 등록되어 있는 상품입니다.")

            await db.item.create(
                data={"name": name, "price": int(price), "end": False},
            )
        return msg("🌿 상품이 성공적으로 등록 되었습니다! :)")
    except Exception as e:
        print(e)
        return msg("🌿 올바른 입력 형식이 아니거나, 에러가 발생했습니다.🥲")
    finally:
        await db.disconnect()


# 🏷️ DONE
############## 상품 테이블 조회 ###############
# item에 등록되어 있는 상품을 모두 조회하여 반환    #
# #########################################
@app.post("/getTable")
async def getTable(req: Dict):
    await db.connect()
    try:
        items = await db.item.find_many()
        reply = {'opened': [], 'closed': []}

        # item을 순회하며 end 값이 true면 reply 'opened'에
        # (name, price) append, false면 'closed'에 append
        reply['opened'] = [{'name': item.name,
                            'price': item.price}
                           for item in items if not item.end]
        reply['closed'] = [{'name': item.name,
                            'price': item.price}
                           for item in items if item.end]
        # reply opened의 데이터들을
        # f"{name} - {price}원\n"{name} - {price}원\n(repeat)..."
        # 형태의 str로 반환
        opened_str = "\n".join(
            [f"▫️ {item['name']} - {item['price']}원" for item in reply['opened']])
        closed_str = "\n".join(
            [f"◾️ {item['name']} - {item['price']}원" for item in reply['closed']])

        reply['opened'] = opened_str
        reply['closed'] = closed_str

        if not reply['opened']:
            reply['opened'] = '🌿 현재 오픈된 상품이 없습니다.'
        if not reply['closed']:
            reply['closed'] = '🌿 현재 마감된 상품이 없습니다.'
        return msg(reply)
    except Exception as e:
        print(e)
        return msg("🌿 상품 조회에 실패했습니다.🥲")
    finally:
        await db.disconnect()


# 🏷️ DONE
############### 상품 마감 ####################
# item 테이블에서 찾은 뒤 마감여부 True로 업데이트  #
###########################################
@ app.post("/endItem")
async def endItem(req: Dict):
    await db.connect()
    try:
        info = req['action']['params']['item_info']
        itemData = info.split(',')

        for item_name in itemData:
            closed = []
            item_name = item_name.strip()
            item = await db.item.find_unique(where={"name": item_name})
            if item:
                await db.item.update(where={"name": item_name}, data={"end": True})
                closed.append(item_name)
            else:
                message = f"🌿 {item_name} 이름의 상품이 없습니다."
                message += f"\n🌿 {', '.join(closed)}는 삭제되었습니다." if len(
                    closed) > 0 else ""
                return msg()
        return msg(f"🌿 총 {len(itemData)}건 마감했습니다. :)")

    except Exception as e:
        print(f'========= {e}')
        return msg("🌿 오류가 발생했습니다. 다시 시도해주세요. :()")
    finally:
        await db.disconnect()


# 🏷️ DONE
############### 상품 삭제 ###################
# item_name에 해당하는 상품을 삭제             #
###########################################
@app.post("/deleteItem")
async def deleteItem(req: Dict):
    await db.connect()
    try:
        deleted = []
        info = req['action']['params']['item_info']
        itemData = info.split(',')

        for item_name in itemData:
            item_name = item_name.strip()
            item = await db.item.find_unique(where={"name": item_name})
            if item:
                await db.item.delete(where={"name": item_name})
                deleted.append(item_name)
            else:
                message = f"🌿 {item_name} 이름의 상품이 없습니다. "
                message += f"\n🌿 {', '.join(deleted)}는 삭제되었습니다." if len(
                    deleted) > 0 else ""
                return msg()
        return msg(f"🌿 총 {len(itemData)}건 삭제되었습니다. :)")

    except Exception as e:
        print(e)
        return msg("🌿 오류가 발생했습니다. 다시 시도해주세요. :(")
    finally:
        await db.disconnect()


# 🏷️ DONE
############### 상품 재오픈 #################
# item_name에 해당하는 상품을 재오픈           #
##########################################
@app.post("/reopenItem")
async def reopenItem(req: Dict):
    await db.connect()
    try:
        info = req['action']['params']['name']
        items = info.split(',')

        success, fail = [], []
        for item_name in items:
            item = await db.item.find_unique(where={"name": item_name})
            if item and item.end:
                await db.item.update(
                    where={"name": item_name}, data={"end": False})
                success.append(item_name)
            else:
                fail.append(item_name)

        message = ""
        message += f"🌿 {' '.join(success)}을 재오픈했습니다."
        if (len(fail) > 0):
            message += f"🌿 {' '.join(fail)} 상품들은 이미 오픈되어 있거나, 해당이름을 찾을 수 없어 재오픈하지 못했습니다 :("
        return msg(message)
    except Exception as e:
        print(e)
        return msg(f"🌿 오류가 발생했습니다. 다시 시도해주세요.")
    finally:
        await db.disconnect()


# 🏷️ DONE
########################## 주문하기 ###########################
# 특정 상품 주문 받기                                           #
# 특정 상품에 대해 order를 새로 생성하는 함수                       #
############################################################
@app.post("/order")
async def order(req: Dict):
    await db.connect()
    try:
        info = req['action']['params']['item_info']
        itemData = info.split(',')

        for idx, item_info in enumerate(itemData):
            cstm, item_name, count, type, deposit = [
                info.strip() for info in item_info.split('/')]

            item = await db.item.find_unique(
                where={"name": item_name})

            if item:
                # 한국기준시 yyyy-mm-dd를 current_date이라는 변수로 저장
                current_date = datetime.now(
                    pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')

                await db.order.create(
                    data={
                        "item_name": item_name,
                        "customer": cstm,
                        "deposit": True if deposit == "입금" else False,
                        "type": type,
                        "count": int(count),
                        "created_at": current_date,
                        "status": "준비 중"
                    }
                )
            else:
                return msg(f"🌿 {item_name}라는 이름의 상품이 없습니다. ")
        return msg(f"🌿 총 {len(itemData)}개 주문이 완료되었습니다. 감사합니다! :)")

    except Exception as e:
        print(e)
        return msg(f"🌿 {idx+1}번째 주문을 처리하던 중 오류가 발생했습니다.")
    finally:
        await db.disconnect()


# 👷🏻‍♂️ ING - [TODO] 특정 기준일(yyyy.mm.dd)을 입력받아 이후 주문만 조회
###################### 전체 주문내역 확인 #######################
# 해당 item에 해당하는 order들을 order에서 조회한 뒤                #
# 각 상품이름(Item table의 item) 별로 order 리스트로 묶어서 반환하시오 #
#############################################################
@app.post("/check_order_list")
async def check_order_list():
    await db.connect()
    try:
        # 현재 item 테이블에 등록된 모든 아이템들의 name 가져오기
        items = await db.item.find_many()
        item_names = [item.name for item in items]  # 리스트로 변환

        res_msg = f"🌿 주문 내역 확인 🌿"
        for item_name in item_names:
            # order table에서 item_name이 item_name인 orders 조회
            orders = await db.order.find_many(where={"item_name": item_name})

            order_msg, total = "", 0
            for order in orders:
                order_msg += f"\n    ◾️ {order.customer} {order.count}건 \
                    \n      [입금] {'✅' if order.deposit else '❌'} [상태] {order.status}"
                total += order.count
            res_msg += f"\n\n▫️ {item_name}: 총 {total} 건"
            res_msg += order_msg

        return msg(res_msg)
    except Exception as e:
        print(e)
        return msg(f"🌿 처리하던 중 오류가 발생했습니다. :(")
    finally:
        await db.disconnect()


# 🏷️ DONE
##################  특정 유저 주문내역 확인  ####################
# Order Table의 현재 상태 조회                                #
###########################################################
@app.post("/customer_order")
async def customer_order(req: Dict):
    await db.connect()
    try:
        user = req['action']['params']['고객 아이디']
        user = user.strip()
        orders = await db.order.find_many(where={"customer": user})

        if len(orders) > 0:
            message = f"🌿 {user} 님의 주문내역입니다. :)"
            for order in orders:
                message += f"\n\n▫️ 주문번호 {(order.created_at).replace('-', '')+str(order.id)}" + \
                    f"\n      {order.item_name} {order.count}건" + \
                    f"\n      [입금] {'✅' if order.deposit else '❌'} [상태] {order.status}"
        else:
            return msg(f"🌿 {user}님은 아직 주문하신 내역이 업습니다. :)")
        return msg(message)

    except Exception as e:
        print(e)
        return msg(f"🌿 주문을 조회하던 중 오류가 발생했습니다.")
    finally:
        await db.disconnect()


# 🏷️ DONE
##################  특정 주문 수정하기  ####################
# 주문번호와 수정하려는 주문 업데이트 하기                      #
#######################################################
@app.post("/update_order")
async def update_order(req: Dict):
    await db.connect()
    try:
        orders_info = req['action']['params']['order']
        orders = orders_info.split(',')

        message = "🌿 아래와 같이 수정되었습니다."
        for order_info in orders:
            order_number, type, content = [
                info.strip() for info in order_info.split('/')]
            id_num = order_number[8:]
            order = await db.order.find_unique(where={"id": int(id_num)})

            if order:
                if type == "수량":
                    # Update the order document with the new information
                    await db.order.update(
                        where={"id": int(id_num)},
                        data={
                            "count": int(content),
                        }
                    )
                    # Return the updated order document
                    message += f"\n\n ▫️ {order.customer}님의 {order.item_name} \
                               상품 주문수량을 [{content}]으로 수정했습니다 :)"
                # 입금내역 수정
                elif type == "입금":
                    await db.order.update(
                        where={"id": int(id_num)},
                        data={
                            "deposit": True if content == "입금" else False
                        }
                    )
                    message += f"\n\n ▫️ {order.customer}님의 {order.item_name} \
                               입금상태를 [{content}]으로 수정했습니다 :)"
                else:
                    message += f"\n\n ▫️ {type}은 업데이트가 불가능한 항목입니다. :("
            else:
                message += f"\n\n ▫️ 주문번호 {order_number}에 해당하는 주문을 찾지 못했습니다. :("
        return msg(message)

    except Exception as e:
        print(e)
        return msg(f"🌿 주문을 조회하던 중 오류가 발생했습니다.")
    finally:
        await db.disconnect()


# 👷🏻‍♂️ ING - [TODO] AI가 정리한 주문 실제 주문으로 저장하기
###################### 이미지 수신  ###########################
# 이미지 수신해서 llama3.2 vision을 OCR로 사용하기.               #
# 해당 item Id를 itemId로 가지는 order 데이터 생성               #
############################################################
@app.post("/imageUrl")
async def image_url(req: Dict):
    # imageURL parsing하기
    url_info = req['action']['params']['imageUrl']
    url_info_json = json.loads(url_info)
    url_str = url_info_json['secureUrls']
    secure_urls_str = url_str[5:-1]
    secure_urls = [url.strip() for url in secure_urls_str.split(',')]

    try:
        results = []
        for url in secure_urls:
            results.extend(perform_ocr(url))

        print(results)

        summary = {}
        for order in results:
            if order['item'] not in summary:
                summary[order['item']] = {'total_count': 0,
                                          'customers': set()}
            summary[order['item']]['total_count'] += order['count']
            summary[order['item']]['customers'].add(
                (order['customer'], order['count']))

        # 결과를 정리한 메세지를 출력
        message = "🌿 이미지 분석결과 입니다."
        for item, info in summary.items():
            message += f"\n🏷️ {item} - {info['total_count']}건"
            for customer, count in info['customers']:
                message += f"\n  ✔️ {customer}: {count}"

        print(message)
        return msg(message)

    except Exception as e:
        print(f"Error: {e}")
        return msg("🌿 문제가 발생했어요. :(")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
