from fastapi import FastAPI, HTTPException, Query, Depends, Header
from pydantic import BaseModel
from database import get_db_connection
from dotenv import load_dotenv
import os

# from fastapi_pagination import Page, paginate, add_pagination
# from fastapi_pagination.bases import AbstractPage

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
#add_pagination(app)

app.add_middleware(CORSMiddleware, expose_headers=['*'], allow_origins=['*'],allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

# Loading .env file for API Key Token
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

# Define Pydantic models for data validation
class PhoneNumber(BaseModel):
    PhoneNumber: str
    Description: str
    IncomingSIPTrunkID: int
    OutgoingSIPTrunkID: int
    FallbackSIPTrunkID: int
    FallbackNumber: str

class SIPTrunk(BaseModel):
    SIPTrunkName: str
    SIPTrunkAddress: str


def verify_token(x_api_token: str = Header(...)):
    print ("API_TOKEN configured is : " + API_TOKEN)
    if x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


# Endpoint to create a PhoneNumber
@app.post("/phonenumbers/")
async def create_item(phonenumber: PhoneNumber, dependencies=[Depends(verify_token)]):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO gozupees_phonenumbers (PhoneNumber,Description,IncomingSIPTrunkID,OutgoingSIPTrunkID,FallbackSIPTrunkID,FallbackPhoneNumber,Status) VALUES (%s,%s,%s,%s,%s,%s,'Active')"
        cursor.execute(query, (phonenumber.PhoneNumber,phonenumber.Description,phonenumber.IncomingSIPTrunkID,phonenumber.OutgoingSIPTrunkID,phonenumber.FallbackSIPTrunkID,phonenumber.FallbackNumber))
        conn.commit()
        return {"message": "PhoneNumber Added successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()


# Example endpoint to get all items
@app.get("/phonenumbers/", dependencies=[Depends(verify_token)])
async def read_items(
            page: int = Query(1, ge=1, description="Page number"),
            page_size: int = Query(10, ge=1, le=100, description="Items per page")
        ):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries

        # get total count
        cursor.execute("SELECT COUNT(*) as total FROM gozupees_phonenumbers")
        total = cursor.fetchone()["total"]

        # compute offset
        offset = (page - 1) * page_size

        cursor.execute("SELECT * FROM gozupees_phonenumbers LIMIT %s OFFSET %s", (page_size, offset))
        items = cursor.fetchall()
        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,  # ceiling division
            "items": items
        }
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()


# Endpoint to delete a phonenumber
@app.delete("/phonenumbers/{phonenumber}",dependencies=[Depends(verify_token)])
async def delete_items(phonenumber: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries
        query = "DELETE FROM gozupees_phonenumbers WHERE PhoneNumber=%s"
        cursor.execute(query, (phonenumber,))
        conn.commit()
        return {"message": "PhoneNumber deleted successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()



# Example endpoint to update all items
#@app.put("/phonenumbers/{phonenumber}")
#async def update_items(phonenumber: str):
#    try:
#        conn = get_db_connection()
#        cursor = conn.cursor(dictionary=True) # Return results as dictionaries
#        query = "UPDATE gozupees_phonenumbers SET title=%s, UpdatedAt=CURRENT_TIMESTAMP WHERE PhoneNumber=%s"
#        cursor.execute(query, (phonenumber))
#        conn.commit()
#        return {"message": "Item updated successfully"}
#    except mysql.connector.Error as err:
#        raise HTTPException(status_code=500, detail=f"Database error: {err}")
#    finally:
#        if conn:
#            conn.close()


# Endpoint to udpate phonenumber status
@app.put("/phonenumbers_statusupdate/{phonenumber,status}", dependencies=[Depends(verify_token)])
async def update_items(phonenumber: str, status: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries
        query = "UPDATE gozupees_phonenumbers SET Status=%s, UpdatedAt=CURRENT_TIMESTAMP WHERE PhoneNumber=%s"
        cursor.execute(query, (status, phonenumber))
        conn.commit()

        if cursor.rowcount == 0:
            return {"message": "PhoneNumber Not Found"}
        else:
            return {"message": "PhoneNumber Status Updated successfully"}

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()

# Endpoint to update phonenumber fallbacknumber
@app.put("/phonenumbers_fallbackupdate/{phonenumber,fallbacknumber}", dependencies=[Depends(verify_token)])
async def update_items(phonenumber: str, fallbacknumber: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries
        query = "UPDATE gozupees_phonenumbers SET FallbackPhoneNumber=%s, UpdatedAt=CURRENT_TIMESTAMP WHERE PhoneNumber=%s"
        cursor.execute(query, (fallbacknumber,phonenumber))
        conn.commit()
        return {"message": "PhoneNumber FallbackNumber Updated successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()



### SIP Trunk/Gateway Management

# Example endpoint to get all SIP Trunks
@app.get("/siptrunks/", dependencies=[Depends(verify_token)])
async def read_items(
            page: int = Query(1, ge=1, description="Page number"),
            page_size: int = Query(10, ge=1, le=100, description="Items per page")
        ):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries

        # get total count
        cursor.execute("SELECT COUNT(*) as total FROM dr_gateways")
        total = cursor.fetchone()["total"]

        # compute offset
        offset = (page - 1) * page_size

        cursor.execute("SELECT gwid AS SIPTrunkID, address AS SIPTrunkAddress, description AS SIPTrunkName from dr_gateways LIMIT %s OFFSET %s", (page_size, offset))
        items = cursor.fetchall()
        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,  # ceiling division
            "items": items
        }
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()


# Endpoint to update a SIP Trunk
@app.put("/siptrunk_update/{siptrunkid}", dependencies=[Depends(verify_token)])
async def update_items(siptrunkid: int, siptrunkinfo: SIPTrunk):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries
        query = "UPDATE dr_gateways SET address=%s, description=%s WHERE gwid=%s"
        cursor.execute(query, (siptrunkinfo.SIPTrunkAddress,siptrunkinfo.SIPTrunkName,siptrunkid))
        conn.commit()

        query = "UPDATE dr_rules SET description=%s WHERE groupid=%s"
        cursor.execute(query, (siptrunkinfo.SIPTrunkName,siptrunkid))
        conn.commit()

        return {"message": "SIP Trunk Updated successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()

# Endpoint to delete a SIP Trunk
@app.delete("/siptrunks/{siptrunkid}", dependencies=[Depends(verify_token)])
async def delete_items(siptrunkid: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries

        query = "DELETE FROM dr_rules WHERE groupid=%s"
        cursor.execute(query, (siptrunkid,))
        conn.commit()

        query = "DELETE FROM dr_gateways WHERE gwid=%s"
        cursor.execute(query, (siptrunkid,))
        conn.commit()

        return {"message": "SIP Trunk deleted successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()


# Endpoint to create a SIPTrunk
@app.post("/siptrunks/", dependencies=[Depends(verify_token)])
async def create_item(siptrunk: SIPTrunk):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO dr_gateways (type,address,strip,pri_prefix,attrs,description) VALUES (0,%s,0,'','',%s)"
        cursor.execute(query, (siptrunk.SIPTrunkAddress,siptrunk.SIPTrunkName))
        conn.commit()

        # Retrieve the last inserted ID
        new_siptrunk_id = cursor.lastrowid


        query = "INSERT INTO dr_rules (groupid,prefix,timerec,priority,routeid,gwlist,description) VALUES (%s,'','',10,0,%s,%s)"
        cursor.execute(query, (new_siptrunk_id,new_siptrunk_id,siptrunk.SIPTrunkName))
        conn.commit()

        return {"message": "SIPTrunk Added successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()
