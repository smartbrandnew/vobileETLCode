#!/usr/bin/env python
#coding:utf8
#Date: 2016-03-14
#Author: cwj
#Desc: data from vtweb to TitleBasedRemoveNum and TitleBasedRemoveNum1
#


from mysqlHelp import MySQLHelper
import ConfigParser
from parseConfig import CfgParser
import sys
import os
import logging
import time
from titleBased import getConfMysqlInfo, getMinDatePara

logger = logging.getLogger("titleBased_remove")
logger.setLevel(logging.DEBUG)
log_file = '/Job/VIACOM/Dashboard/TitleBasedStaging/log/titleBased_remove.log'
filehandler = logging.handlers.RotatingFileHandler(filename=log_file, maxBytes=5*1024*1024, backupCount=10, mode='a')
formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

cfg_file = "/Job/VIACOM/Dashboard/TitleBasedStaging/conf/viacom_dashboard.cfg"
if not os.path.exists(cfg_file):
	logging.debug(": config file not exists") 
	sys.exit(0)
#################################################################################################################################
logger.info(": extract data from tracker2 start")
# extract dat from vtweb
date_para_TitleBasedRemoveNum_min = getMinDatePara(table_name = "TitleBasedRemoveNum", date_para = "takeoffDate")
if date_para_TitleBasedRemoveNum_min == None:
	date_para_TitleBasedRemoveNum_min = "2015-02-28"
print date_para_TitleBasedRemoveNum_min
date_para_TitleBasedRemoveNum_max = time.strftime("%Y-%m-%d", time.localtime(time.time() - 0 * 24 * 60 * 60))

date_para_TitleBasedRemoveNum_dict = {"date_para_TitleBasedRemoveNum_min":date_para_TitleBasedRemoveNum_min, \
	"date_para_TitleBasedRemoveNum_max":date_para_TitleBasedRemoveNum_max, "min_report_date": "2015-03-01"}
vt_TitleBasedRemoveNum_SQL = """
	select
	  date_format(a.created_at, "%%Y-%%m-%%d") as reportDate,
	  date_format(a.takeoff_time, "%%Y-%%m-%%d") as takeoffDate,
	  a.trackingWebsite_id,
	  a.trackingMeta_id,
	  count(*) removedNum,
	  sum(case when a.first_send_notice_date >0 and a.takeoff_time>0  
	  	then TIMESTAMPDIFF(MINUTE, a.first_send_notice_date, a.takeoff_time) else 0  end) as complianceTime,
	  CURRENT_TIMESTAMP as ETLDate
	from tracker2.matchedVideo as a, mddb.trackingWebsite as b
	where a.trackingWebsite_id = b.id
	  and a.company_id = 14
	  and (b.website_type = "ugc" or b.website_type = "hybrid")
	  and a.count_send_notice > 0
	  and hide_flag = 2
	  and a.first_send_notice_date < a.takeoff_time
	  and a.first_send_notice_date > 0
	  and a.created_at >= "%(min_report_date)s"
	  and date_format(a.takeoff_time, "%%Y-%%m-%%d") > "%(date_para_TitleBasedRemoveNum_min)s"
	  and date_format(a.takeoff_time, "%%Y-%%m-%%d") < "%(date_para_TitleBasedRemoveNum_max)s"
	group by 1, 2, 3, 4
	UNION ALL
	select
	  date_format(a.created_at, "%%Y-%%m-%%d") as reportDate,
	  date_format(a.takeoff_time, "%%Y-%%m-%%d") as takeoffDate,
	  a.trackingWebsite_id,
	  a.trackingMeta_id,
	  count(*) removedNum,
	  sum(case when a.first_send_notice_date >0 and a.takeoff_time>0  
	  	then TIMESTAMPDIFF(MINUTE, a.first_send_notice_date, a.takeoff_time) else 0  end) as complianceTime,
	  CURRENT_TIMESTAMP as ETLDate
	from tracker2.matchedVideo as a, mddb.trackingWebsite as b, tracker2.matchedFileItem d
	where a.trackingWebsite_id = b.id
	  and d.matchedFile_id =  a.matchedFile_id
	  and a.company_id = 14
	  and b.website_type = "cyberlocker"
	  and a.count_send_notice > 0
	  and hide_flag = 2
	  and a.first_send_notice_date < a.takeoff_time
	  and a.first_send_notice_date > 0
	  and a.created_at >= "%(min_report_date)s"
	  and date_format(a.takeoff_time, "%%Y-%%m-%%d") > "%(date_para_TitleBasedRemoveNum_min)s"
	  and date_format(a.takeoff_time, "%%Y-%%m-%%d") < "%(date_para_TitleBasedRemoveNum_max)s"
	group by 1, 2, 3, 4
""" %date_para_TitleBasedRemoveNum_dict

#vtweb_tracker2_section = "vtweb_tracker2"
vtweb_tracker2_section = "vtweb_staging"
try:
	vt_host, vt_user, vt_passwd, vt_port, vt_db = getConfMysqlInfo(vtweb_tracker2_section)
	vtweb_mysql = MySQLHelper(host=vt_host, user=vt_user,passwd=vt_passwd, port = vt_port, db_name = vt_db)
	vtweb_mysql.queryCMD("set time_zone = '-5:00'")
	result = vtweb_mysql.queryCMD(vt_TitleBasedRemoveNum_SQL)
except Exception, e:
	logger.debug(": extract data from vt for TitleBasedRemoveNum, %s" %e)
	sys.exit(0)
finally:
	vtweb_mysql.closeCur()
	vtweb_mysql.closeConn()
	logger.info(": extract data from tracker2 end")

logger.info(":load data to TitleBasedRemoveNum  start")
target_server_section = "target_server_staging"
target_host, target_user, target_passwd, target_port, target_db= getConfMysqlInfo(target_server_section)
try:
	target_mysql = MySQLHelper(host=target_host, user=target_user, passwd=target_passwd, 
		db_name = target_db, port = target_port, charset = 'utf8')
	insert_SQL = """
		INSERT INTO TitleBasedRemoveNum(reportDate, takeoffDate, trackingWebsite_id, 
			trackingMeta_id, removedNum, complianceTime, ETLDate) 
		VALUES(%s, %s, %s, %s, %s, %s, %s)
	"""
	target_mysql.executeManyCMD(insert_SQL, result)
	target_mysql.commit()
except Exception, e:
	logger.debug(": load data to TitleBasedRemoveNum, %s" %e)
	sys.exit(0)
finally:
	target_mysql.closeCur()
	target_mysql.closeConn()
	logger.info(":load data to TitleBasedRemoveNum  end")
#################################################################################################################################
logger.info(":extract data from TitleBasedRemoveNum  start")
target_server_section = "target_server_staging"
try:
	target_mysql = MySQLHelper(host=target_host, user=target_user, passwd=target_passwd, db_name = target_db, port = target_port, charset = 'utf8')
	aggregate_SQL = """
		select
		  a.reportDate,
		  a.takeoffDate,
		  a.trackingWebsite_id,
		  a.websiteName,
		  a.websiteType,
		  ifnull(b.metaTitle, a.title) as title,
		  sum(removedNum) as removedNum,
		  sum(complianceTime) as complianceTime,
		  current_timestamp as ETLDate
		from
		  (select
		  a.reportDate,
		  a.takeoffDate,
		  a.trackingWebsite_id,
		  c.websiteName,
		  c.websiteType,
		  b.title,
		  sum(removedNum) as removedNum,
		  sum(complianceTime) as complianceTime
		  from TitleBasedRemoveNum as a, TitleBasedMeta as b, TitleBasedTrackingWebsite as c
		  where a.trackingWebsite_id = c.trackingWebsite_id
		    and a.trackingMeta_id = b.trackingMeta_id
		  group by 1, 2, 3, 4, 5, 6) as a
		left join MetaTitleMapTitle as b
		on a.title = b.metaTitle
		group by 1, 2, 3, 4, 5, 6
	"""
	print "===================="
	aggregate_result = target_mysql.queryCMD(aggregate_SQL)
	
	print aggregate_result[1]
	insertUpdate_SQL = """
		INSERT INTO TitleBasedRemoveNum1 
			(reportDate, takeoffDate, trackingWebsite_id, websiteName, 
				websiteType, title, removedNum, complianceTime,  ETLDate) 
  		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
  		ON DUPLICATE KEY UPDATE 
  			removedNum = VALUES(removedNum), complianceTime = VALUES(complianceTime), ETLDate = VALUES(ETLDate)
	"""
	target_mysql.insertUpdateCMD(insertUpdate_SQL, aggregate_result)
	target_mysql.commit()
except Exception, e:
	logger.debug(" load data to TitleBasedRemoveNum1, %s" %e)
	sys.exit(0)
finally:
	target_mysql.closeCur()
	target_mysql.closeConn()
	logger.info(" load data to TitleBasedRemoveNum1  end")
#################################################################################################################################
#sed  "/\/home\/vobile\/cwj\/ViacomProject\/dashboard\/job/\/Job\/VIACOM\/Dashboard\/TitleBased/g"


