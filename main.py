from fastapi import FastAPI, HTTPException, Query, Depends, Header, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import get_db_connection
from dotenv import load_dotenv
import os
import io
import csv
import codecs
import pandas as pd
import httpx

# from fastapi_pagination import Page, paginate, add_pagination
# from fastapi_pagination.bases import AbstractPage

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
#add_pagination(app)

app.add_middleware(CORSMiddleware, expose_headers=['*'], allow_origins=['*'],allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

# Loading .env file for API Key Token
#load_dotenv()
#API_TOKEN = os.getenv("API_TOKEN")
API_TOKEN="wd0bms/F0WQsngRBq-nZuJ-jT5LCR=ljRqo=rtnVPsQLkMxunkYCQZlqNp2JGBcm"

client = httpx.AsyncClient()

# Define Pydantic models for data validation
class PhoneNumber(BaseModel):
    PhoneNumber: str
    Description: str
    IncomingSIPTrunkID: int
    OutgoingSIPTrunkID: int
    FallbackSIPTrunkID: int
    FallbackPhoneNumber: str

class PhoneNumberUpdate(BaseModel):
    PhoneNumber: str
    Description: str
    IncomingSIPTrunkID: int
    OutgoingSIPTrunkID: int
    FallbackSIPTrunkID: int
    FallbackPhoneNumber: str
    Status: str

class PhoneNumberStatus(BaseModel):
    PhoneNumber: str
    Status: str

class PhoneNumberFallbackNumber(BaseModel):
    PhoneNumber: str
    FallBackNumber: str

class SIPTrunk(BaseModel):
    SIPTrunkName: str
    SIPTrunkAddress: str


# Define a Pydantic model for the data to be sent to the external API
# Define the fixed JSON payload
KAMAILIO_DR_PAYLOAD = {
    "jsonrpc": "2.0",
    "method": "drouting.reload",
    "id": 1
}

# Define a Pydantic model for the data received from the external API
class ExternalApiResponse(BaseModel):
    status: str
    message: str

def verify_token(x_api_token: str = Header(...)):
    if x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


# Endpoint to bulk receive PhoneNumbers Data
@app.post("/phonenumbers-bulk-upload/", dependencies=[Depends(verify_token)])
async def upload_csv_bulk(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Uploads a CSV file, processes its data in bulk, and returns a JSON response. \n
    CSV FILE TEMPLATE (Required Fields):\n        
    PhoneNumber,  Description, IncomingSIPTrunkID,OutgoingSIPTrunkID,FallbackSIPTrunkID,FallbackPhoneNumber \n
    CSV FILE EXAMPLE VALUES :
    \n "+44712345678", "UK Mobile", "1", "2", "3", "+447111222333"\n
    IncomingSIPTrunkID: Mention the SIP Trunk ID where the Calls to PhoneNumber (Active State) should be routed to \n
    OutgoingSIPTrunkID: Mention the SIP Trunk ID where the Calls from this PhoneNumber should be routed to \n
    FallbackSIPTrunkID: Mention the SIP Trunk ID where the Calls to this PhoneNumber (Suspended State) should be routed to 

    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    try:
        # Read the file content
        # Use codecs.iterdecode for robust handling of various encodings
        csv_reader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
        
        # Convert CSV data to a list of dictionaries
        data = list(csv_reader)

        # Add a background task to close the file after the response is sent
        background_tasks.add_task(file.file.close)

        # Process the data in bulk (example: add a new field)
        processed_data = []

        conn = get_db_connection()
        for row in data:

            try:

                cursor = conn.cursor()
                query = "INSERT INTO gozupees_phonenumbers (PhoneNumber,Description,IncomingSIPTrunkID,OutgoingSIPTrunkID,FallbackSIPTrunkID,FallbackPhoneNumber,Status) VALUES (%s,%s,%s,%s,%s,%s,'Active')"
                print ("CSV data : "+ row['PhoneNumber'] + " " + row['Description'] + row['IncomingSIPTrunkID'] + " " + row['OutgoingSIPTrunkID'] + " " + row['FallbackSIPTrunkID'] + " " + row['FallbackPhoneNumber'])
                cursor.execute(query, (row['PhoneNumber'],row['Description'],row['IncomingSIPTrunkID'],row['OutgoingSIPTrunkID'],row['FallbackSIPTrunkID'],row['FallbackPhoneNumber']))
                conn.commit()

                # Example processing: adding a 'status' field
                row['status'] = 'processed'
                processed_data.append(row)

            except mysql.connector.Error as err:
                raise HTTPException(status_code=500, detail=f"Database error: {err}")

        return JSONResponse(content={"message": "CSV uploaded and processed successfully", "data": processed_data})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {e}")

    finally:
        if conn:
            conn.close()

# Endpoint to create a PhoneNumber
@app.post("/phonenumbers/", dependencies=[Depends(verify_token)])
async def create_item(phonenumber: PhoneNumber):
    """
    IncomingSIPTrunkID: Mention the SIP Trunk ID where the Calls to PhoneNumber (Active State) should be routed to \n
    OutgoingSIPTrunkID: Mention the SIP Trunk ID where the Calls from this PhoneNumber should be routed to \n
    FallbackSIPTrunkID: Mention the SIP Trunk ID where the Calls to this PhoneNumber (Suspended State) should be routed to
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO gozupees_phonenumbers (PhoneNumber,Description,IncomingSIPTrunkID,OutgoingSIPTrunkID,FallbackSIPTrunkID,FallbackPhoneNumber,Status) VALUES (%s,%s,%s,%s,%s,%s,'Active')"
        cursor.execute(query, (phonenumber.PhoneNumber,phonenumber.Description,phonenumber.IncomingSIPTrunkID,phonenumber.OutgoingSIPTrunkID,phonenumber.FallbackSIPTrunkID,phonenumber.FallbackPhoneNumber))
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


# Phonenumbers endpoint to update all items
@app.put("/phonenumbers/", dependencies=[Depends(verify_token)])
async def update_items(phonenumber: PhoneNumberUpdate):
    """
    IncomingSIPTrunkID: Mention the SIP Trunk ID where the Calls to PhoneNumber (Active State) should be routed to \n
    OutgoingSIPTrunkID: Mention the SIP Trunk ID where the Calls from this PhoneNumber should be routed to \n
    FallbackSIPTrunkID: Mention the SIP Trunk ID where the Calls to this PhoneNumber (Suspended State) should be routed to
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries

        if phonenumber.Status == 'Ported':
            query = "UPDATE gozupees_phonenumbers SET Description=%s,IncomingSIPTrunkID=%s,OutgoingSIPTrunkID=%s,FallbackSIPTrunkID=%s,FallbackPhoneNumber=%s,Status=%s,UpdatedAt=CURRENT_TIMESTAMP, PortedMarkedAt=CURRENT_TIMESTAMP WHERE PhoneNumber=%s"
        else:
            query = "UPDATE gozupees_phonenumbers SET Description=%s,IncomingSIPTrunkID=%s,OutgoingSIPTrunkID=%s,FallbackSIPTrunkID=%s,FallbackPhoneNumber=%s,Status=%s,UpdatedAt=CURRENT_TIMESTAMP, PortedMarkedAt=NULL WHERE PhoneNumber=%s"
        cursor.execute(query, (phonenumber.Description,phonenumber.IncomingSIPTrunkID,phonenumber.OutgoingSIPTrunkID,phonenumber.FallbackSIPTrunkID,phonenumber.FallbackPhoneNumber,phonenumber.Status,phonenumber.PhoneNumber))
        conn.commit()
        return {"message": "PhoneNumber updated successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()

# Endpoint to udpate phonenumber status
@app.put("/phonenumbers_statusupdate/", dependencies=[Depends(verify_token)])
async def update_items(phonenumber: PhoneNumberStatus):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries

        if phonenumber.Status == 'Ported':
            query = "UPDATE gozupees_phonenumbers SET Status=%s, UpdatedAt=CURRENT_TIMESTAMP, PortedMarkedAt=CURRENT_TIMESTAMP WHERE PhoneNumber=%s"
        else:
            query = "UPDATE gozupees_phonenumbers SET Status=%s, UpdatedAt=CURRENT_TIMESTAMP, PortedMarkedAt=NULL WHERE PhoneNumber=%s"

        cursor.execute(query, (phonenumber.Status, phonenumber.PhoneNumber))
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
@app.put("/phonenumbers_fallbackupdate/", dependencies=[Depends(verify_token)])
async def update_items(phonenumber: PhoneNumberFallbackNumber):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries
        query = "UPDATE gozupees_phonenumbers SET FallbackPhoneNumber=%s, UpdatedAt=CURRENT_TIMESTAMP WHERE PhoneNumber=%s"
        cursor.execute(query, (phonenumber.FallBackNumber,phonenumber.PhoneNumber))
        conn.commit()
        return {"message": "PhoneNumber FallbackPhoneNumber Updated successfully"}
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

"""
# Endpoint to delete a ported phonenumbers post 30 Days of marked as Ported
@app.delete("/phonenumbers-ported-clean",dependencies=[Depends(verify_token)])
async def delete_items_ported():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries
        query = "DELETE FROM gozupees_phonenumbers WHERE Status='Ported' AND DATE_ADD(PortedMarkedAt, INTERVAL 30 MINUTE) < CURRENT_TIMESTAMP"
        cursor.execute(query)
        conn.commit()
        return {"message": "Ported PhoneNumbers deleted successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()
"""

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

        result = await reload_kamailio_drouting()

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

        result = await reload_kamailio_drouting()

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

        result = await reload_kamailio_drouting()

        return {"message": "SIPTrunk Added successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn:
            conn.close()

# Function to call Kamailio DROUTING RELOAD
async def reload_kamailio_drouting():
        """
        Fetches data from an external HTTP URL asynchronously.
        """
        url = "http://127.0.0.1:9090/RPC"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url,json=KAMAILIO_DR_PAYLOAD)
                response.raise_for_status()  # Raise an exception for bad status codes
                return response.json()
            except httpx.RequestError as exc:
                print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
                return {"error": "Failed to fetch data from external service"}
            except httpx.HTTPStatusError as exc:
                print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc}")
                return {"error": f"External service returned status {exc.response.status_code}"}

