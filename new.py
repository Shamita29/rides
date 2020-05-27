from flask import Flask,request, jsonify,render_template,abort, session,Response
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import datetime 
import os
import re
import requests
import hashlib 
from sqlalchemy.sql import select,exists
from sqlalchemy.orm import load_only
import csv
import sys, time
from sqlalchemy.orm import backref

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'rideshare.db')
db = SQLAlchemy(app)
ma = Marshmallow(app)



class User(db.Model):

    __tablename__ = "user"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(128))
    #fkey = db.relationship('Ride', back_populates='parent')
    posts = db.relationship('UserRide', backref='user', lazy='dynamic')
    ride = db.relationship('Ride', cascade='all,delete',secondary= 'user_ride', backref='user')

    def __init__(self, username, password):
    	self.username = username
    	self.password = password

    def serialize(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'password':self.password}


class Ride(db.Model):

    __tablename__ = "ride"

    ride_id = db.Column(db.Integer,autoincrement=True,primary_key=True)
    created= db.Column(db.String(50), nullable=False)
    src_adr= db.Column(db.String(50), nullable=False)
    dest_adr = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.String(50))
    #user_id = db.Column(db.Integer, db.ForeignKey('user.user'), nullable=False)
    #parent = db.relationship('User')


    #rides = db.relationship('User', backref='ride', passive_deletes=True)
    def serialize(self):
        #return "<Ride ride_id=%s created=%s source_adr=%s dest_adr=%s timestamp=%s>" % (self.ride_id, self.created,
        return {
        'ride_id':self.ride_id,
        'created':self.created,
        'src_adr':self.src_adr,
        'dest_adr':self.dest_adr,
        'timestamp':self.timestamp,
        }

class UserRide(db.Model):

    __tablename__ = "user_ride"

    user_ride_id = db.Column(db.Integer,
                          autoincrement=True,
                          primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey("ride.ride_id"), nullable=False)
    ride = db.relationship('Ride', uselist=False) 


    def __repr__(self):
        s = "<UserRide user_ride_id=%s user_id=%s ride_id=%s >"
        return s % (self.user_ride_id, self.user_id, self.ride_id)

class joinRide(db.Model):
    __tablename__ = "userdetails"

   
    user_ride_id = db.Column(db.Integer,
                          autoincrement=True,
                          primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey("ride.ride_id"), nullable=False)
    ride = db.relationship('Ride', uselist=False)  

    def serialize(self):
        return {
        'user_ride_id':self.user_ride_id,
        'username':self.username,
        'ride_id':self.ride_id
        
        }

class DataDisplay(ma.Schema):
    class Meta:
        fields = ('username','password','user_id','ride_id','created','src_adr','dest_adr','timestamp')


data_display = DataDisplay()
datas_display = DataDisplay(many=True)

def formatTheDate(s):    
    line=s.split(" ")
    yymmdd=line[0].split('-')
    hhms=line[1].split(':')
    yy=yymmdd[0]
    mm=yymmdd[1]
    dd=yymmdd[2]
    hh=hhms[0]
    m=hhms[1]
    s=str(int(float(hhms[2])))
    return(dd+'-'+mm+'-'+yy+':'+s+'-'+m+'-'+hh)
    

def is_in_format(s):
    if(re.match(r'[0-3]{2}-[0-9]{2}-[0-9]{4}:[0-5][0-9]-[0-5][0-9]-[0-5][0-9]',s) is None):
        return 1
    else:
        return 0

def checkingArea(num):
    file=open("AreaNameEnum.csv","r")
    line={}
    i=0;
    for lines in file:
        if i==0:
            i+=1
        else:
            l=lines.split(',')
            line[int(l[0])]=int(l[0])
    file.close()
    return (num in line)

def isupcoming(data1,data2):
    line1=data1.split(':')
    line2=data2.split(':')
    date1=line1[0]
    time1=line1[1]
    date2=line2[0]
    time2=line2[1]
    result=comparewithdate(date1,date2)
    if(result==1):
        return True
    elif result==0:
        return comparewithtime(time1,time2)
    else:
        return False

def comparewithtime(time1,time2):
    arg1=time1.split('-')
    arg2=time2.split('-')
    l=list(zip(arg1,arg2))
    l.reverse()
    for(j,i) in l:
        i=int(i)
        j=int(j)
        if(i>j):
            return True
        elif i<j:
            return False
def comparewithdate(date1,date2):
    ddmmyy1=date1.split('-')
    ddmmyy2=date2.split('-')
    result=-1
    l=list(zip(ddmmyy1,ddmmyy2))
    l.reverse()
    for(j,i) in l:
        i=int(i)
        j=int(j)
        if(i>j):
            result=1
            break
        elif i==j:
            result=0
        else:
            result=-1
            break
    return result


@app.route("/api/v1/users", methods=["PUT"])
def add_user():
    if (request.method=="PUT"):
        _username = request.json['username']
        _password = request.json['password']
        result = hashlib.sha1(_password.encode()) 
        pwd=result.hexdigest()
        if(re.match(r'[0-9a-fA-F]{40}$',_password) is None):
            return jsonify({"flag":"password mismatch"}),400
        else:

        	readquery={
        	"table":"user",
        	"query":"searchuser",
        	"where":"username",
            "data":_username
        	}
        	
        	read=readdb(readquery)
        	if read==200:
        		return jsonify({}),400
        	else:
        		sqlquery={"table":"user","query":"insert","username":_username, "password":pwd}
        		#que={"usern":_username,"password":pwd}s
        		res=writedb(sqlquery)
        		if res==200:
        			return jsonify({}),201
        		else:
        			return Response(status=400)
    else:
        return Response(status=405)



@app.route("/api/v1/users/<username>", methods=["DELETE"])
def user_delete(username):
    #print(username)
    readquery={"table":"user","column":"user","where":"username", "data":username}
    read=readdb(readquery)
    if read==200:
        sqlquery={"table":"user","query":"delete","usern":username}
        res=writedb(sqlquery)
        print(res)
        if res==200:
            return jsonify({}),200
        else:
            return Response(status=204)
    else:
        return Response(status=204)
    

@app.route("/api/v1/users",methods=["GET"])
def list_users():
    readquery={"table":"userlist","query":"listuser"}
    res=readdb(readquery)
    if res==204:
        return {},204
    else:
        return jsonify(res),200


@app.route("/api/v1/rides",methods=["POST"])
def create_ride():
	if(request.method=="POST"):
		createdby = request.json['created_by']
		src = request.json['source']
		dest = request.json['destination']
		timestamp= request.json['timestamp']
		if (is_in_format(timestamp)):
			if((checkingArea(src)) and  (checkingArea(dest)) and (src != dest)):
				readquery={"table":"user","column":"user","where":"username","data":createdby}
				read=readdb(readquery)
				if read==200:
					sqlquery={"table":"ride","query":"insert","name":createdby,"source":src, "destiny":dest,"date":timestamp}
					res=writedb(sqlquery)
					if res==200:
						return jsonify({}),201
					else:
						return Response(status=204)
				else:
					return Response(status=400)

			else:
				return Response(status=405)
		else:
			return Response(status=400)
	else:
		return Response(status=405)



@app.route("/api/v1/rides",methods=["GET"])
def ride_details():
        if request.method=="GET":
            src=int(request.args.get("source"))
            dest=int(request.args.get("destination"))
            tm=formatTheDate(str(datetime.datetime.now()))
            if( (checkingArea(src)) and  (checkingArea(dest)) and (src != dest)):
                query=db.session.execute('select ride_id,created,timestamp from ride where src_adr={} and dest_adr={}'.format(src,dest))
                #res=datas_display.dump(query)
                #print(res)
                list_ = []
                for record in query:
                    recordObject = {}
                    recordObject["ride_id"]=record[0]
                    recordObject["created"]=record[1]
                    if(isupcoming(tm,record[2])):
                        recordObject["time"]=record[2]
                        list_.append(recordObject)
                if len(list_)!=0:
                    return jsonify(list_),200
                else:
                    return {},204
            
        else:
            return {},405

@app.route("/api/v1/rides/<ride_id>",methods=["GET"])
def list_ride(ride_id):
    if(request.method=="GET"):
        readquery={"table":"ridess","id":ride_id,"query":"list"}
        res=readdb(readquery)
        if res==400:
            return Response(status=204)
        else:
            return jsonify(res),200
    else:
        return Response(status=405)


@app.route("/api/v1/rides/<ride_id>",methods=["POST"])
def join_ride(ride_id):
    if(request.method=="POST"):
        _usern=request.json['username']
        readquery={"table":"rideid","column":"ride_id","where":"ride_id","id":ride_id}
        num=readdb(readquery)
        if num==200:
            readquery={"table":"user","column":"username","where":"username","data":_usern}
            res=readdb(readquery);
            if res==200:
                readquery={"table":"rides","id":ride_id,"query":"join"}
                createdby=readdb(readquery)
                if(createdby[0] != _usern):
                    sqlquery={"table":"details", "query":"insert","usernn":_usern, "rides":ride_id}
                    result=writedb(sqlquery); #adding users to join ride
                    if result==201:
                        return jsonify({}),201
                    else:
                        return Response(status=204)
                else:
                    return {},400
            else:
                  return Response(status=400)
        else:
            return Response(status=204)
    else:
        return Response(status=405)


@app.route("/api/v1/rides/<id>",methods=["DELETE"])
def delete_ride(id):
    if(request.method=="DELETE"):
        readquery={"table":"rideid","column":"ride_id","where":"ride_id","id":id}
        res=readdb(readquery)
        if res==200:
            sqlquery={"table":"ride","query":"delete","insert":id}
            result=writedb(sqlquery)
            if result==200:
            	return Response(status=200)
            else:
            	return Response(status=204)
        else:
        	return Response(status=204)   
    else:
        return Response(status=405)

def writedb(sqlquery):
    if 'insert' in sqlquery['query']:
    	if 'user' in sqlquery['table']:
            nuser="{}".format(sqlquery['username'])
            pwdd="{}".format(sqlquery['password'])
            useradd = User(username=nuser,password=pwdd)
            db.session.add(useradd)
            db.session.commit()
            return 200
    	if 'ride' in sqlquery['table']:
        	by="{}".format(sqlquery['name'])
        	pick="{}".format(sqlquery['source'])
        	dest="{}".format(sqlquery['destiny'])
        	schedule="{}".format(sqlquery['date'])
        	rideadd = Ride(created=by,src_adr=pick,dest_adr=dest,timestamp=schedule)
        	db.session.add(rideadd)
        	db.session.commit()
        	return 200
    	if 'details' in sqlquery['table']:
        	nuserr="{}".format(sqlquery['usernn'])
        	uid="{}".format(sqlquery['rides'])
        	new_ride = joinRide(username=nuserr, ride_id=uid)
        	db.session.add(new_ride)
        	db.session.commit()
        	return 201 
            
    if 'delete' in sqlquery['query']:
    	if 'user' in sqlquery['table']:
            nuser="{}".format(sqlquery['usern'])
            existing_user = User.query.filter(User.username == nuser).first()
            if existing_user:
                    new2=Ride.query.filter(Ride.created ==  nuser).first()
                    if new2:
                        db.session.delete(new2)
                        db.session.delete(existing_user)
                        db.session.commit()
                        return 200
                    else:
                        db.session.delete(existing_user)
                        db.session.commit()
                        return 200

    	if 'ride' in sqlquery['table']:
    		rides="{}".format(sqlquery['insert'])
    		#print(rides)
    		new2=Ride.query.filter(Ride.ride_id == rides).first()
    		db.session.delete(new2)
    		db.session.commit()
    		return 200

    if 'clear' in sqlquery['query']:
        if 'user' in sqlquery['table']:
            userlist=db.session.execute('select * from user');
            res=datas_display.dump(userlist)
            if res:
                db.session.execute('delete from user');
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=204)

        if 'ride' in sqlquery['table']:
            userlist=db.session.execute('select * from ride');
            res=datas_display.dump(userlist)
            if res:
                db.session.execute('delete from ride');
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=204)

        if 'userride' in sqlquery['table']:
            userlist=db.session.execute('select * from user_ride');
            res=datas_display.dump(userlist)
            if res:
                db.session.execute('delete from user_ride');
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=204)

        if 'userdetails' in sqlquery['table']:
            userlist=db.session.execute('select * from userdetails');
            res=datas_display.dump(userlist)
            if res:
                db.session.execute('delete from user');
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=204)

def readdb(readquery):
    if "user" in readquery['table']: 
        if readquery['data']:
            uname="{}".format(readquery['data'])
            existing_user = User.query.filter(User.username == uname).first()
            if existing_user:
                return 200 

    if "userlist" in readquery['table']:
        query=db.session.execute('select username from user')
        if query:
            result= datas_display.dump(query)
            return result
        else:
            return 204


    if 'ridedetails' in readquery['table']:
        res=db.session.execute('select ride_id,created,timestamp from ride     where src_adr={} and dest_adr={}'.format(readquery['source'],['destiny']))
        if res:
            result = datas_display.dump(res)
            return result
        else:
            return 204


    
    if "ridess" in readquery['table']:
        if "list" in readquery['query']:
            rides="{}".format(readquery['id'])
            existing_user = Ride.query.filter(Ride.ride_id == rides).first()
            if existing_user:
                userlist=db.session.execute('select username from userdetails where ride_id={}'.format(readquery['id']))
                res=datas_display.dump(userlist)
                records = db.session.execute('select ride_id,created,src_adr,dest_adr,timestamp from ride where ride_id={}'.format(readquery['id']))
                for record in records:
                    recordObject = { 'ride_id':record.ride_id,
                    'created_by': record.created,
                            'source': record.src_adr,
                            'users':[],
                            'destination': record.dest_adr,
                            'timestamp': record.timestamp}

                for names in res:
                    recordObject["users"].append(names["username"])
                #recordObject['users'].append(user)

                return recordObject
            else:
                return 400

    if "rideid" in readquery['table']:
            if readquery['id']:
                datas="{}".format(readquery['id'])
                existing_user = Ride.query.filter(Ride.ride_id == datas).first()
                if existing_user:
                    return 200

    if "rides" in readquery['table']:
        rides="{}".format(readquery['id'])
        createdby=db.session.execute('select created from ride where ride_id={}'.format(readquery['id'])).first()
        res=datas_display.dump(createdby)
        return res


if __name__ == "__main__":
    app.debug = True
    app.run()