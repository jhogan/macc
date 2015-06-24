#! /usr/bin/python

from dt import *
from err import *
from commandline import *
from acc import *
import readline
import sys
import traceback
import subprocess
from business import *

class macccmdline(cmdline):
    def __init__(self):
        self._curacct=None
        self._prevacct=None
        cmdline.__init__(self)

    def currentaccount(self, v=0):
        if v!=0: 
            cur=self._curacct
            if cur != v:
                self.previousaccount(cur)
            self._curacct=v
        return self._curacct

    def previousaccount(self, v=0):
        if v!=0:
            self._prevacct=v
        return self._prevacct

    def cmdclass(self):
        if self.cmd() == None:
            return None

        return self.cmd() + 'cmd'

    def exe(self):
        if not self.isvalid():
            raise InvalidCommandError(self)

        c=globals()[self.cmdclass()](self)

        if not c.isvalid():
            raise InvalidCommandError(c)

        c.exe()
            
    def autocompleter(self, txt, state):
        chopped=[]
        try:
            r=[]
            self._line=readline.get_line_buffer()
            self.cursorix(readline.get_endidx())
            last=self.lastword()
            if self.atendofcmd() or \
                    self.cmd()=='help':
                for c in command.allcmds():
                    if c.startswith(txt):
                        r.append(c+' ')
            else:
                #print "<%s, %s>" % (txt, state)
                curacct=self.currentaccount()

                if not last:
                    acct=curacct
                else: 
                    if last.startswith('/'):
                        acct=accounts.getroot()
                        last=last.lstrip('/')
                    else:
                        acct=curacct

                    chopped=last.rsplit('/',1)
                    tmpacct=acct.getsubaccount(chopped[0])

                    if tmpacct: acct=tmpacct

                    if len(chopped) > 1:
                        txt=chopped[1]
                    
                for a in acct.accounts(): 
                    if txt=='' or a.name().startswith(txt):
                        r.append(a.name() + '/')
                if len(r) == 1:
                    readline.insert_text('/')
            try:
                return r[state]
            except IndexError:
                return None

        except Exception, ex:
            print "%s:\n%s\n%s" % \
                   ("autocompleter exception", type(ex), str(ex))
            print "txt: %s; state: %s" % (txt, state)
            print "chopped: " + str(chopped)
            print "last: " + last

    def cmd(self):
        if inp.rstrip().startswith('!'):
            return 'shell'
        return cmdline.cmd(self)

    def invalidreason(self):
        c=self.cmd()
        if c == None:
            return None
        elif c not in command.allcmds():
            return "%s: not found" % c
        return None

class command(object):
    _opts=""
    def __init__(self, cl):
        self._cl=cl

    def currentaccount(self):
        return self.cmdline().currentaccount()

    def noargs(self):
        return self.args().len()==0

    def invalidreason(self):
        for arg in self.cmdline().args(self):
            if not self._isoptionallowed(arg.name()):
                return "Option %s is not allowed" % arg.name()
        return self._invalidreason()

    def _invalidreason(self):
        raise NotImplementedError("_invalidreason is abstract")
           
    def isvalid(self):
        return self.invalidreason() == None

    @staticmethod
    def allcmds():
        r=[]
        for c in command.__subclasses__():
            name=c.__name__[:-3]
            r.append(name)
        return r


    def cmdline(self):
        return self._cl

    def args(self):
        return self.cmdline().args(self)

    def _requiresvalue(self, opt):
        return opt + ":" in self._opts

    def _isoptionallowed(self, opt):
        return opt in self._opts

    def exe(self):
        raise NotImplementedError("exe is abstract")

    def name(self):
        return type(self).__name__[:-3]

class mkdircmd(command):
    def _invalidreason(self):
        if self.noargs():
            return "missing operands"
        
    def exe(self):
        curacct=self.currentaccount()
        for arg in self.args():
            if arg.isanon():
                arg=arg.value()
                relative=not arg.startswith('/')

                if relative:
                    acct=curacct
                else:
                    acct=accounts.getroot()

                acct.newsubacct(arg)

class rmcmd(command):
    def _invalidreason(self):
        if self.noargs():
            return "missing operand"

    def exe(self):
        cl=self.cmdline()
        for acct in self.accounts2remove():
            acct.path()
            res=cl.prompt("remove account: %s" % acct.path(), 'yna', True)
            if res == 'y':
                acct.remove()
            elif res == 'a':
                break

    def accounts2remove(self):
        r=[]
        curacct=self.cmdline().currentaccount()
        for arg in self.args():
            path=arg.value()
            if path.startswith('/'):
                r.append(accounts.getaccount(path))
            else:
                r.append(curacct.getsubaccount(path))
        return r
            
class txcmd(command):
    _opts='d:m:'
    def exe(self):
        args=self.args()

        if self.args().len() == 1:
            self.show()

        self.update()

    def ix(self):
        return \
            self.args().whereint()[0].value()

    def tx(self):
        cl=self.cmdline()
        txs=cl.currentaccount().totransactions()
        return txs.get(self.ix())

    def update(self):
        args=self.args()
        tx = self.tx()
        for arg in args:
            opt=arg.name()
            if opt=='d':
                tx.date(arg.value())
            elif opt=='a':
                tx.dollars(arg.value())
            elif opt=='m':
                tx.memo(arg.value())

    def show(self):
        cl=self.cmdline()
        tx=self.tx()
        dt=tx.date()
        memo=tx.memo()
        amt=tx.dollars()

        cl.printline( "%s\t%s\t%s" % (str(dt), memo, amt) )

    def _invalidreason(self):
        if self.noargs():
            return "No arguments given"
        
class lscmd(command):
    def exe(self):
        cl=self.cmdline()
        txs=cl.currentaccount().totransactions()
        for i in range(txs.len()):
            tx=txs[i]
            dt=tx.date()
            memo=tx.memo()
            amt=tx.dollars()
            cl.addtoprintbuffer(i, dt, memo, amt)
        cl.printbuffer()
    def _invalidreason(self):
        return None

class cdcmd(command):
    def _invalidreason(self):
        if self.cmdline().argsline().strip() == '-':
            return None
        if self.noargs():
            return "Must specify one account path"
        elif len(self.args()) > 1:
            return "Only one argument required"

    def exe(self):
        if self.noargs():
            if self.cmdline().argsline().strip() == '-':
                acct=self.cmdline().previousaccount()
                if not acct: 
                    msg="No previous account set"
                    raise CommandFailError(msg)
            else:
                # We should never get here
                msg="Must specify one account path"
                raise CommandFailError(msg)
        else:
            path=self.args()[0].value()
            curacct=self.cmdline().currentaccount()

            if path.startswith("/"):
                acct=accounts.getaccount(path)
            else: 
                acct=curacct.getsubaccount(path)
       
        if not acct:
            msg="cd: %s: No such account" % path
            raise CommandFailError(msg)
        self.cmdline().currentaccount(acct)

class shellcmd(command):
    def _invalidreason(self):
        return None
    
    def exe(self):
        line=self.cmdline().line()
        line=line.lstrip("   !")
        subprocess.Popen(line).communicate()

class helpcmd(command):
    pass

bom=business_object_manager.getinstance()
bom.connections().add("/tmp/my.db")
bom.connections().createtables()

a=account(1, override=True)

a.name("derp")
a.enabled()
a.enabled(False)
a.save()


        


aroot=accounts.getroot()
aexp=account('exp', True)
anull=account('null', True)
abook=account('book', True)
autil=account('util', True)
awan=account('wan', True)
acell=account('cell', True)
acable=account('cable', True)
aservers=account('servers', True)

aroot.accounts().add( (aexp, anull) )
aexp.accounts().add( (abook, awan) )
awan.accounts().add( (acell, acable, aservers) )

acct=anull

txs=transactions('/home/ubuntu/trunks/macc/tmp/chk.qfx')
anull._totransactions=txs

readline.parse_and_bind('tab: complete')

cl=macccmdline()
cl.currentaccount(acct)
readline.set_completer(cl.autocompleter)



while True:
    try:
        inp=raw_input("macc:%s$ " % cl.currentaccount().path())
    except KeyboardInterrupt:
        print "^C"
        continue
    except EOFError:
        sys.exit(1)

    try:
        cl.line(inp)

        if cl.cmd() != None:
            cl.exe()
    except (CommandFailError, InvalidCommandError) as err:
        print(str(err))
    except Exception as err:
        print(str(err))
        traceback.print_exc()
        
    

