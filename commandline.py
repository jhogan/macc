#! /usr/bin/python
from dt import *
import sys
from err import *
import os
import subprocess

class cmdline:
    def __init__(self):
        self._line=''
        self._curacct=None
        self._printbuffer=[]
        self._cmdlinecharacters=None
        self._pipelinecharacters=None
        self._redirect=None
        self._pipeprocess=None
        self._stdout=None

    def clearlinecache(self):
        self._cmdlinecharacters=None
        self._pipelinecharacters=None

    class chars(col):
        def __init__(self):
            col.__init__(self)

        def str(self):
            r=''
            for c in self: r+=c.value()
            return r

        def add(self, c=None):
            if c==None: c=cmdline.char()
            if isinstance(c, str):
                c=cmdline.char(c)
            col.add(self, c)
            return c
        
            
    class char:
        def __init__(self, c):
            self._escaped=False
            self._escape=False
            self._indoublequotes=False
            self._insinglequotes=False
            self._c=c

        def escape(self, v=None):
            if v!=None:
                self._escape=v
            return self._escape

        def escaped(self, v=None):
            if v!=None:
                self._escaped=v
            return self._escaped
        
        def insinglequotes(self, v=None):
            if v!=None:
                self._insinglequotes=v
            return self._insinglequotes

        def indoublequotes(self, v=None):
            if v!=None:
                self._indoublequotes=v
            return self._indoublequotes

        def inquotes(self):
            return self.insinglequotes() or \
                   self.indoublequotes()

        def __str__(self):
            return self.value()

        def value(self):
            return self._c
                


    def find(self, s, inquotes=True):
        s_len=len(s); ix=0
        cs=self.cmdlinecharacters()
        found=[]
        for i in range(len(cs)):
            c=cs[i]
            if c.escape(): continue
            if not inquotes and c.inquotes():
                continue

            if str(c) == s[ix]:
                found.append(str(c))
                ix+=1
            else:
                if ix>0:
                    del found[:]; ix=0
                
            if len(found) == len(s):
                return i - (len(found) - 1)
        return -1

    def pipelinecharacters(self):
        self.setcharacters()
        return self._pipelinecharacters

    def cmdlinecharacters(self):
        self.setcharacters()
        return self._cmdlinecharacters

    def setcharacters(self):
        if not self._cmdlinecharacters:
            clcs=self._cmdlinecharacters=cmdline.chars()
            self._pipelinecharacters=cmdline.chars()
            afterpipe=inesc=False
            insinglequotes=indoublequotes=False
            for c in self.line():
                if not insinglequotes and  \
                    not indoublequotes and \
                    not inesc and \
                    not afterpipe and \
                    c == "|": 
                        clcs=self._pipelinecharacters
                        afterpipe=True
                        continue
                
                clc=clcs.add(c)
                if c == "\\":
                    if inesc:
                        inesc=False
                        clc.escaped(True)
                    else:
                        inesc=True
                        clc.escape(True)
                        continue

                if inesc:
                    inesc=False
                    clc.escaped(True)

                if c == "'":
                    if not clc.escaped():
                        insinglequotes=not insinglequotes
                        continue

                if c == '"':
                    if not clc.escaped():
                        indoublequotes=not indoublequotes
                        continue

                clc.insinglequotes(insinglequotes)
                clc.indoublequotes(indoublequotes)
        return self._cmdlinecharacters

    def pipeline(self):
        cs=self.pipelinecharacters()
        if not cs: return None
        return cs.str()
        
    def pipein(self):
        pp=self.pipeprocess()
        if pp:
            return pp.stdin
        return None

    def pipeprocess(self):
        if not self._pipeprocess:
            pipe=self.pipeline()
            if not pipe: return None
            PIPE=subprocess.PIPE
            p=subprocess.Popen(pipe, 
                                stdin=PIPE,
                                shell=True)
            self._pipeprocess=p
        return self._pipeprocess

    def redirect(self):
        if not self._redirect:
            pipe=self.pipeprocess()
            if pipe: return None
            ix=self.find('>>', 
                     inquotes=False)

            if ix>-1:
                ix += 1
                mode='a' # append
            else:
                ix=self.find('>', inquotes=False)
                if ix>-1: mode='w' # clobber

            if ix>-1:
                line=self.cmdlinecharacters().str()
                ix+=1
                redirectfile=line[ix:].strip()
                if len(redirectfile) > 0:
                    if os.path.isdir(redirectfile):
                        raise CommandlineParseError('%s: Is a directory"')
                    self._redirect=open(redirectfile, mode)
                else:
                    msg="syntax error near unexpected token `newline'"
                    raise CommandlineParseError(msg)
            return self._redirect
                
    def prompt(self, msg, opts=None, forcevalid=False):
        if opts:
            for c in opts:
                c=c.lower()
                if   c=='y':
                    msg += " %s" % "[y]es"
                elif c=='n':
                    msg += " %s" % "[n]o"
                elif c=='c':
                    msg += " %s" % "[c]ancel"
                elif c=='a':
                    msg += " %s" % "[a]abort"
            msg += ' '

        # todo: should this use self.stdin?
        while True:
            res=raw_input(msg)
            res = res.strip().lower()
            if opts:
                if len(res) == 1 and res not in opts: res='I' # 'I'==invalid
                if not (res == 'I' and forcevalid):
                    break
        return res

    def stdout(self):
        if not self._stdout:
            p=self.pipein()
            if p:
                self._stdout=p
            else:
                r=self.redirect()
                if r: 
                    self._stdout=r
                else:
                    self._stdout=sys.stdout

        return self._stdout

    def addtoprintbuffer(self, *args):
        self._printbuffer.append(list(args))
    
    def _formatbuffer(self):
        maxcols=[]
        for cols in self._printbuffer:
            for i in range(len(cols)):
                if len(maxcols) < i+1:
                    maxcols.append(0)
                col=str(cols[i])
                lencol=len(col)
                if maxcols[i]<lencol:
                    maxcols[i]=lencol
        
        for cols in self._printbuffer:
            for i in range(len(cols)):
                col=str(cols[i])
                cols[i]=col.ljust(maxcols[i]+1)

    def printbuffer(self, line=None):
        self._formatbuffer()
        lines= self._printbuffer

        for line in lines:
            for col in line:
                self.print_(col)
            self.printline()
        self._close_stdout()
        self._printbuffer=[]

    def _close_stdout(self):
        stdout=self.stdout()
        if not stdout.isatty():
            self._redirect=None
            
            pp=self.pipeprocess()

            if pp:
                out,err = pp.communicate()
                if out:
                    sys.stdout.write(out)
                if err:
                    sys.stderr.write(err)
                self._pipeprocess=None

            stdout.close()
        self._stdout=None

    def print_(self, s):
        self.stdout().write(s)

    def printline(self, line=""):
        self.print_(line + "\n")

    def name(self): return 'msh'

    def cursorix(self,v=None):
        if v!=None: 
            self._cursorix=v
        return self._cursorix

    def atendofcmd(self):
        ix=self.cursorix()
        line=self._line
        beforecursor=line[0:ix]
        if len(line)>ix:
            return cmdline.haswhitespace(line[ix:ix+3])
        return not cmdline.haswhitespace(beforecursor) 
                
    @staticmethod
    def haswhitespace(s):
        return  ' '  in s or \
                "\t" in s


    def line(self,v=None):
        if v!=None: 
            if self._line != v:
                self.clearlinecache()
            self._line=v
        return self._line

    def lastword(self):
        r=''
        ix=self.cursorix()
        line=self.line()
        for i in range(ix - 1, -1,-1):
            if line[i] in (" ", "\t"): break
            r=line[i]+r
        if r=='': r=None
        return r

    def cmd(self):
        return self._split(0)

    def args(self, cmd):
        # Create args collection. This will  be returned.
        r=arguments()
        opts=cmd._opts
        line=self.argsline()
        if line == None: return r
        inesc=insinglequotes=indoublequotes=fillingoptname=False
        previnquotes=inquotes=fillingvalue=False
        a=None

        escaped=False
        # iterate over the argument portion of the command line
        for i in range(len(line)):
            # If the last character was escaped
            # then make sure we are no longer in escape mode
            if escaped: escaped=False

            c=line[i] # get the character

            # Get the index of the character in the line.
            # This is useful for exception reporting.
            ix = i + len(self.cmd()) + 1

            # If c is a backslash then set then inesc
            # is True. That way the next iteration will
            # be an escaped character.
            if c == '\\':
                if not inesc:
                    inesc=True
                    continue
                else:
                    inesc=False
            else:
                if inesc: # Last char was a backslash
                    if inquotes:
                        if c in ("'", '"'):
                            escaped=True
                        else:
                            # Create a new argument object (a) 
                            # if it doesn't exist and append
                            # c to its .value attribute.
                            if not a: a=r.add()
                            a.value(a.value() + "\\" + c)
                            escaped=False
                            inesc=False
                            continue

                    elif c not in (' ', "'", '"'):
                        msg="%s not escapable at charcter: %s" % (c, ix)
                        raise CommandlineParseError(msg)
                    escaped=True
                    inesc=False

            if c == "'":
                if not escaped: # If the quote was not escaped
                    if not indoublequotes:
                        insinglequotes=not insinglequotes

            if c == '"':
                if not escaped: # If the quote was not escaped
                    if not insinglequotes:
                        indoublequotes=not indoublequotes

            previnquotes=inquotes
            inquotes=indoublequotes or insinglequotes
            
            if previnquotes and not inquotes:
                previnquotes=fillingvalue=False
                continue

            if not previnquotes and inquotes:
                continue
                        
            # fillingoptname is True if we have come across
            # a '-' and are ready to collect the name of the 
            # option. 
            if fillingoptname:
                if c == '-':
                    # If a dash is in the option name then
                    # it is an error.
                    raise CommandlineParseError("To many dashes at " + ix)
                if a:
                    # a (an argument object) will exist
                    # we've begun filling in the value.
                    if len(a.name()) == 1:
                        # If the parameter requires a value
                        # collect here.
                        if cmd.optrequiredvalue(a.name()):

                            # Allow for whitespace between option
                            # and value, e.g., -m "my message"
                            # todo: remove
                            #if c not in (' ', '\t'): 
                            if not c.isspace():
                                a.value(c)
                                fillingvalue=True
                                fillingoptname=False
                        else:
                            # No value required so we are
                            # done with this option
                            a=None
                            fillingoptname=False
                else:
                    # Instantiate an argument object and 
                    # set the name to c
                    a=r.add()
                    a.name(c)
                    
            # We are filling in a.value with 
            # the current character. The value
            # could be that of a parameter, e.g., -d myvalue,
            # or just a string hanging out on the command line, e.g.,
            # cmd myvalue escaped\ value 
            # This command has 2 values: myvalue and "escaped value"
            elif fillingvalue:
                    if c == ' ' and not escaped and not inquotes:
                        fillingvalue=False
                        a=None
                    else:
                        a.value(a.value() + c)
            else:
                # If we are here, then we are trying to
                # determine if we are to start an argument
                # with an option (-d) or an anonymous 
                # argument (an argument string that is not proceeded
                # by an option).
                if not inquotes:
                    if c == '-':
                        fillingoptname=True
                    if c in ('-', ' ', '\t'):
                        continue

                a=r.add()
                a.value(c)
                fillingvalue=True

        if inquotes:
            # Were done iterating over the line's characters. Why
            # are we still in a quote then?
            raise CommandlineParseError("EOL while scanning literal string")
        
        if a and a.value() == "" and cmd.optrequiresvalue(a.name()):
            # An option was found that requires a value but
            # the value was not supplied. 
            msg="%s requires a value" % a.name()
            raise CommandlineParseError(msg)

        # Return the collection of argument objects
        return r

    def argsline(self):
        return self._split(1)

    def _split(self, ix):
        l=self.cmdlinecharacters().str()
        try:    return l.split(None,1)[ix]
        except: return None

    def isvalid(self):
        return self.invalidreason() == None

    def invalidreason(self):
        return None

class arguments(col):
    def __init__(self):
        col.__init__(self)

    def add(self, o=None):
        if o == None:
            o=argument()
        col.add(self, o)
        return o

    def whereint(self):
        r=arguments()
        for arg in self:
            if arg.isint():
                r.add(arg)
        return r

class argument:
    def __init__(self):
        self._name=''
        self._value=''

    def name(self, v=None):
        if v != None: self._name=v
        return self._name


    def valuetyped(self):
        if self.isint():
            return int(self._value)
        elif self.isfloat():
            return float(self._value)
        return self._value

    def value(self, v=None):
        if v != None: self._value=v
        return self._value

    def isanon(self):
        return self.name() == ""

    def __str__(self):
        name=self.name()
        value=self.value()
        if self.isanon():
            name="<anon>"
        return "%s = \"%s\"" % (name, value)

    def isint(self):
        try:
            int(self._value)
            return True
        except: return False

    def isfloat(self):
        try:
            float(self._value)
            return True
        except: return False
