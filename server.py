import uvicorn

from utils import msg
from typing import Dict
from chain import chain
from pprint import pprint
from prisma import Prisma
from fastapi import FastAPI
from typing import List, Union
from langserve import add_routes
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
                return msg("🌿 이미 등록되어 있는 상품으로 등록을 취소합니다.")

            await db.item.create(
                data={"name": name, "price": int(price), "end": False},
            )
        return msg("🌿 상품이 성공적으로 등록 되었습니다!")
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


############### 상품 마감 ###################
# item_name에 해당하는 상품을                 #
# item 테이블에서 찾은 뒤 마감여부 True로 업데이트 #
###########################################
@ app.post("/endItem")
async def endItem(req: Dict):
    await db.connect()
    try:
        item_name = req['action']['params']['name']
        item = await db.item.find_unique(where={"name": item_name})
        if item:
            await db.item.update(where={"name": item_name}, data={"end": True})
            return msg(f"{item_name} 마감했습니다.")
        else:
            return msg("해당하는 이름의 상품이 없습니다.")
    except Exception as e:
        print(e)
        return msg("오류가 발생했습니다. 다시 시도해주세요.")
    finally:
        await db.disconnect()


############### 상품 삭제 ###################
# item_name에 해당하는 상품을 삭제             #
###########################################
@ app.post("/deleteItem")
async def deleteItem(req: Dict):
    await db.connect()
    try:
        item_name = req['action']['params']['name']
        item = await db.item.find_unique(where={"name": item_name})
        if item:
            await db.item.delete(where={"name": item_name})
            return msg(f"{item_name}을 삭제했습니다.")
        else:
            return msg("해당하는 이름의 상품이 없습니다.")
    except Exception as e:
        print(e)
        return msg("오류가 발생했습니다. 다시 시도해주세요.")
    finally:
        await db.disconnect()


############### 상품 재오픈 #################
# item_name에 해당하는 상품을 재오픈           #
##########################################
@ app.post("/reopenItem")
async def reopenItem(req: Dict):
    await db.connect()
    try:
        item_name = req['action']['params']['name']
        item = await db.item.find_unique(where={"name": item_name})
        if item:
            if item.end:
                await db.item.update(where={"name": item_name}, data={"end": False})
                return msg(f"{item_name}을 재오픈했습니다.")
            else:
                return msg("이미 오픈된 상태입니다.")
        else:
            return msg("해당하는 이름의 상품이 없습니다.")
    except Exception as e:
        print(e)
        return msg(f"오류가 발생했습니다. 다시 시도해주세요.")
    finally:
        await db.disconnect()


###################### 주문내역 확인 ###########################
# 현재 마감이 되지 않은 상품들(end=false)만 item에서 조회하고         #
# 해당 item에 해당하는 order들을 order에서 조회한 뒤                #
# 각 상품이름(Item table의 item) 별로 order 리스트로 묶어서 반환하시오 #
#############################################################
# @app.get("/orders")
# async def check_order():
#     end_false_items = await Item.filter(end=False)
#     order_dict = defaultdict(list)
#     for item in end_false_items:
#         orders = await Order.filter(item=item).prefetch_related("customer")
#         for order in orders:
#             customer_phone = order.customer.phone_number


###################### 주문내역 확인 ###########################
# 현재 Item에 해당하는 이름의 상품이 있는지 확인(end=False)           #
# 해당 item Id를 itemId로 가지는 order 데이터 생성                 #
#############################################################
# @app.post("/create_order")
# async def create_order(item_id: int, customer_id: int):
#     item = await Item.get(id=item_id)
#     if item.end:
#         raise HTTPException(
#             status_code=400, detail="This item is no longer available.")
#     order = await Order.create(item=item, customer_id=customer_id)
#     return order


class InputChat(BaseModel):
    """Input for the chat endpoint."""

    messages: List[Union[HumanMessage, AIMessage, SystemMessage]] = Field(
        ...,
        description="The chat messages representing the current conversation.",
    )


# add_routes(app, rag_chain, path="/rag", enable_feedback_endpoint=True,
#            enable_public_trace_link_endpoint=True,)
# add_routes(app, chain, path="/chain")
# add_routes(app, path="/addItem")
# add_routes(app, path="/endItem/{item_name}")
# add_routes(app, path="/deleteItem/{item_name}")
# add_routes(app, path="/reopenItem/{item_name}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
