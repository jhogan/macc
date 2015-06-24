from dt import *
from ofx_parse import *
from ofx import *
from business import business, nochg
class accounts(col):
    def __init__(self, parent=None):
        col.__init__(self)
        self._parent=parent

    root=None
    @staticmethod
    def getroot():
        if not accounts.root:
            accounts.root=account('', True)
        return accounts.root

    @staticmethod
    def getaccount(path):
        acct=accounts.getroot()
        for name in path.split('/'):
            if name == '' or name == '.': 
                continue

            if name == "..":
                if not acct.isroot():
                    acct=acct.parent()
            else:
                acct=acct.accounts().get(name)

            if not acct: break # acct !exist

        return acct

    def parent(self):
        return self._parent

    def add(self, acct):
        if isinstance(acct, collections.Iterable):
            for a in acct:
                self.add(a)
        else:
            acct._parent=self.parent()
            col.add(self, acct)

        
class account(business):

    def __init__(self, id=None, override=False):
        if not override:
            msg="Use accounts.getaccount(path) to get an account"
            raise Exception(msg)
        self._accounts=accounts(self)
        #self._name=name
        self._parent=None
        self._enabled=True
        business.__init__(self, id)

    zrm_name="varchar(250) not null"
    def name(self, v=None):
        if v!=None:
            self._name=v
        return self._name

    zrm_enabled="bit default 1"
    def enabled(self, v=nochg):
        return self.prop(v)

    def accounts(self):
        return self._accounts

    def totransactions(self):
        return self._totransactions

    def __eq__(self, acct):
        if not acct: return False
        return self.path() == acct.path()

    def remove(self):
        self.parent().accounts().remove(self)

    def newsubacct(self, path):
        acct=self
        for name in path.split('/'):
            if name == '': continue

            accts=acct.accounts()
            acct=accts[name]
            if not acct:
                acct=account(name, override=True)
                accts.add(acct)


    def getsubaccount(self, path):
        path=self.path() + '/' + path
        r=accounts.getaccount(path)
        return r

    def path(self):
        if self.isroot(): return '/'
        r=""; 
        rent=self

        while rent:
            r=rent.name() +  r
            if rent.name()!='': r='/'+r
            rent=rent.parent()
            
        return r

    def isroot(self):
        return not self.parent()

    def parent(self):
        return self._parent

    def str(self):
        return self.name()

class transactions(col):
    def __init__(self, ofx=None):
        col.__init__(self)
        if ofx:
            self._loadofx(ofx)

    def _loadofx(self, ofxfile):
        ofx = OfxParser.parse(file(ofxfile))
        txs=ofx.bank_account.statement.transactions
        for tx in txs:
            self.add(transaction(tx))
            

class transaction(business):
    zrm_fk="account.id"
    zrm_tablename="transaction_"

    def __init__(self, ofxtx=None):
        if ofxtx:
            tx=ofxtx_dederp(ofxtx)
            self.dollars(tx.amt())
            self.date(tx.date())
            self.memo(tx.memo())
            self.name(tx.name())
            self.payee(tx.payee())
            self.type(tx.type())

    def cents(self, v=None):
        if v!= None:
            self._cents=v
        return self._cents

    def dollars(self, v=None):
        if v != None:
            self.cents(v*100)
        return self.cents() * .01

    def date(self, v=None):
        if v!=None: self._date=v
        return self._date

    def memo(self, v=None):
        if v!=None: self._memo=v
        return self._memo

    def name(self, v=None):
        if v!=None: self._name=v
        return self._name
    
    def payee(self, v=None):
        if v!=None: self._payee=v
        return self._payee

    def type(self, v=None):
        if v!=None: self._type=v
        return self._type

    def __repr__(self):
        return "%s\t%s\t%s" % (self.date(),
                            self.memo(),
                            self.dollars())
