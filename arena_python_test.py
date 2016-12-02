import sys

def main(argv):                         
    if argv[1]=='new_trades':
		import ael
		ael.connect('ldnfrl01:7101',argv[2],argv[3])
		date=argv[4] + ' 00:00'
		selectString="t.trdnbr, i.insid, i.isin, t.price, sum(t.quantity*i.contr_size), t.time, display_id(t,'prfnbr'), display_id(t,'Curr'), t.status, ut.userid, cp.ptyid, display_id(t,'sales_person_usrnbr'), t.sales_credit, add_info(t,'Sales Credit MarkUp')"
		fromString="instrument i, trade t, user ut, party cp"
		whereString="i.insaddr=t.insaddr and t.counterparty_ptynbr*=cp.ptynbr and t.trader_usrnbr*=ut.usrnbr and t.status not in ('Void', 'Simulated', 'Valuation') and t.time>='"+date+"'"
		x=ael.asql('select ' + selectString + ' from ' + fromString + ' where '+ whereString)
		print x
		ael.disconnect()
    if argv[1]=='new_trades_running':
		import ael
		import time
		ael.connect('ldnfrl01:7101',argv[2],argv[3])
		date=argv[4] + ' 00:00'
		selectString="t.trdnbr, i.insid, i.isin, t.price, sum(t.quantity*i.contr_size), t.time, display_id(t,'prfnbr'), display_id(t,'Curr'), t.status, ut.userid, cp.ptyid, display_id(t,'sales_person_usrnbr'), t.sales_credit, add_info(t,'Sales Credit MarkUp')"
		fromString="instrument i, trade t, user ut, party cp"
		whereString="i.insaddr=t.insaddr and t.counterparty_ptynbr*=cp.ptynbr and t.trader_usrnbr*=ut.usrnbr and t.status not in ('Void', 'Simulated', 'Valuation') and t.time>='"+date+"'"
		while True:
			ael.poll()
			text_file = open('output.txt', 'w')
			x=ael.asql('select ' + selectString + ' from ' + fromString + ' where '+ whereString)
			text_file.write(str(x))
			text_file.close()
			time.sleep(30)
		ael.disconnect()


if __name__ == "__main__":
    main(sys.argv)