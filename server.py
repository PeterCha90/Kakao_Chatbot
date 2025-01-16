import json
import uvicorn

from utils import msg
from typing import Dict
from pprint import pprint
from prisma import Prisma
from fastapi import FastAPI
from typing import List, Union
from langserve import add_routes
from llama_vision import perform_ocr
from pydantic import BaseModel, Field
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


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


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/chain")


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


############## 상품 테이블 조회 ###############
# item에 등록되어 있는 상품을 모두 조회하여 반환    #
# #########################################
@app.post("/getTable")
async def getTable(req: Dict):
    await db.connect()
    try:
        items = await db.item.find_many()
        pprint(items)
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
            reply['opened'] = '🌿 현재 등록된 상품이 없습니다.'
        if not reply['closed']:
            reply['closed'] = '🌿 현재 마감된 상품이 없습니다.'
        pprint(reply)
        return msg(reply)
    except Exception as e:
        print(e)
        return msg("🌿 상품 조회에 실패했습니다.🥲")
    finally:
        await db.disconnect()


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
        return msg("🌿\n오류가 발생했습니다. 다시 시도해주세요. :()")
    finally:
        await db.disconnect()


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


############### 상품 재오픈 #################
# item_name에 해당하는 상품을 재오픈           #
##########################################
@app.post("/reopenItem")
async def reopenItem(req: Dict):
    await db.connect()
    try:
        item_name = req['action']['params']['name']
        item = await db.item.find_unique(where={"name": item_name})
        if item:
            if item.end:
                await db.item.update(where={"name": item_name}, data={"end": False})
                return msg(f"🌿 {item_name}을 재오픈했습니다.")
            else:
                return msg(f"🌿 {item_name} 이미 오픈된 상태입니다.")
        else:
            return msg("🌿 해당하는 이름의 상품이 없습니다. :(")
    except Exception as e:
        print(e)
        return msg(f"🌿 오류가 발생했습니다. 다시 시도해주세요.")
    finally:
        await db.disconnect()


###################### 주문내역 확인 ###########################
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
            cstm, item_name, count, type, deposit = item_info.split('/')
            print(cstm, item_name, count, type, deposit)

            item_name = item_name.strip()
            item = await db.item.find_unique(where={"name": item_name})

            if item:
                await db.order.create(
                    data={
                        "item_name": item_name,
                        "customer": cstm,
                        "deposit": True if deposit == "입금" else False,
                        "type": type,
                        "count": int(count)
                    }
                )
            else:
                return msg(f"🌿 {item_name}라는 이름의 상품이 없습니다. ")
        return msg(f"🌿 총 {len(itemData)}개 주문이 완료되었습니다. :)")

    except Exception as e:
        print(e)
        return msg(f"🌿 {idx+1}번째 주문을 처리하던 중 오류가 발생했습니다.")
    finally:
        await db.disconnect()


#####################  테스트🧪 완료  #########################


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

        order_dict = {}
        for item_name in item_names:
            # order table에서 item_name이 item_name인 order의 모든 row 갯수 세기
            order_count = await db.order.count(where={"item_name": item_name})
            order_dict[item_name] = order_count

        print(order_dict)
        # order_dict에 있을 데이터에 맞춰 string만들기
        res_msg = f"🌿 주문 내역 확인 🌿"
        for item_name, count in order_dict.items():
            res_msg += f"\n▫️ {item_name}: {count} 건"
        return msg(res_msg)
    except Exception as e:
        print(e)
        return msg(f"🌿 처리하던 중 오류가 발생했습니다.")
    finally:
        await db.disconnect()


##################  특정 유저 주문내역 확인    ####################
# Order Table의 현재 상태 조회                                  #
#############################################################
@app.post("/list_of_order")
async def list_of_order(req: Dict):
    # item = await Item.get(id=item_id)
    # if item.end:
    #     raise HTTPException(
    #         status_code=400, detail="This item is no longer available.")
    # order = await Order.create(item=item, customer_id=customer_id)
    return order


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
                summary[order['item']] = {'total_count': 0, 'customers': set()}
            summary[item['item']]['total_count'] += item['count']
            summary[item['item']]['customers'].add(
                (item['customer'], item['count']))

        # 결과를 정리한 딕셔너리를 출력
        for item, info in summary.items():
            print(f"Item: {item}")
            print(f"Total Count: {info['total_count']}")
            print("Customers:")
            for customer, count in info['customers']:
                print(f"  {customer}: {count}")

        # trim the final message
        message = """
        🌿 이미지 분석결과 입니다.
        """
        print(message)
        # return msg(message)

    except Exception as e:
        print(f"Error: {e}")
        return msg("🌿 문제가 발생했어요. :(")


class InputChat(BaseModel):
    """Input for the chat endpoint."""

    messages: List[Union[HumanMessage, AIMessage, SystemMessage]] = Field(
        ...,
        description="The chat messages representing the current conversation.",
    )


# add_routes(app, rag_chain, path="/rag", enable_feedback_endpoint=True,
#            enable_public_trace_link_endpoint=True,)
# add_routes(app, chain, path="/chain")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
