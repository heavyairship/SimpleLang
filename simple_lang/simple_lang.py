# SimpleLang
#
# FixMe: make evaluation iterative not recursive to avoid max recursion depth errors
# FixMe: try to do faster copies/copy on write for lists, maps, etc.
# FixMe: allow comments
# FixMe: add messages for parse/eval errors
# FixMe: should if/while create their own lexical scopes?
#
# Grammar:
#
# E -> (expression)
# | T
# | (E1
# | E;E2
#
# E1 -> (expression helper)
# | func v P: E)
# | call E L)
# | let v E)
# | mut v E)
# | set v E)
# | UOP E)
# | BOP E E)
# | TOP E E E)
# | E)
#
# E2 -> (expression helper)
# | ε
# | E
#
# T -> (term)
# | n
# | b
# | s
# | v
# | [L]
# | {M}
# | nil
#
# M -> (mapping
# | ε
# | M2
#
# M2 -> (mapping helper)
# | E:E M
#
# P -> (param list)
# | ε
# | P2
#
# P2 -> (param list helper)
# | v P
#
# L -> (expression list)
# | ε
# | L2
#
# L2 -> (expression list helper)
# | E L
#
# UOP -> (unary operator)
# | !
# | head
# | tail
# | print
#
# BOP -> (binary operator)
# | &&
# | ||
# | ==
# | !=
# | <
# | <=
# | >
# | >=
# | +
# | -
# | *
# | /
# | while
# | push
# | get
#
# TOP -> (ternary operator)
# | if
# | put
#
# b -> (boolean atom)
# | True
# | False
#
# n -> (integer atom)
# | [-]*[0-9]+
#
# s -> (string atom) # double quotes surrounding any ascii character
# | "[\x00-\x7F]+"
#
# v -> (variable) # FixMe: var/id should be different
# | [a-zA-Z]+[a-zA-Z0-9]/{True, False}

import enum
import json
import copy
import pdb

##################################################################################
# Utility functions
##################################################################################


def alpha(val):
    if val is None:
        return False
    for c in val:
        ordc = ord(c.lower())
        if ordc not in range(ord('a'), ord('z') + 1):
            return False
    return True


def numeric(val):
    if val is None:
        return False
    for c in val:
        ordc = ord(c)
        if ordc not in range(ord('0'), ord('9') + 1):
            return False
    return True


def alphanumeric(val):
    if val is None:
        return False
    for c in val:
        if not (alpha(c) or numeric(c)):
            return False
    return True


def isspace(val):
    if val is None:
        return False
    return val.isspace()

##################################################################################
# Tokenizer
##################################################################################


QUOTE = '"'


@enum.unique
class TokenType(enum.Enum):
    WHILE = "while"
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LEFT_BRACKET = "["
    RIGHT_BRACKET = "]"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    COLON = ":"
    IF = "if"
    FUNC = "func"
    CALL = "call"
    LET = "let"
    MUT = "mut"
    SET = "set"
    NOT = "!"
    AND = "&&"
    OR = "||"
    EQ = "=="
    NOT_EQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    SEQ = ";"
    HEAD = "head"
    TAIL = "tail"
    PUSH = "push"
    GET = "get"
    PUT = "put"
    PRINT = "print"
    TRUE = "True"
    FALSE = "False"
    NIL = "nil"
    INT = enum.auto()
    VAR = enum.auto()
    STR = enum.auto()


class Token(object):
    def __init__(self, typ, val):
        if not type(typ) is TokenType:
            raise TypeError
        if type(val) not in [int, str] and val is not None:
            raise TypeError
        self.typ = typ
        self.val = val

    def __str__(self):
        return "%s%s" % (self.typ.name, "("+str(self.val)+")" if self.val is not None else "")


KEYWORDS = [
    TokenType.WHILE.value,
    TokenType.IF.value,
    TokenType.FUNC.value,
    TokenType.CALL.value,
    TokenType.LET.value,
    TokenType.MUT.value,
    TokenType.SET.value,
    TokenType.TRUE.value,
    TokenType.FALSE.value,
    TokenType.NIL.value,
    TokenType.HEAD.value,
    TokenType.TAIL.value,
    TokenType.PUSH.value,
    TokenType.GET.value,
    TokenType.PUT.value,
    TokenType.PRINT.value
]


class Tokenizer(object):
    def __init__(self, src):
        self.src = src
        self.end = len(self.src)
        self.idx = 0
        self.tokens = []

    def peek(self, n=1):
        if self.idx+n > self.end:
            return None
        return self.src[self.idx: self.idx+n]

    def at(self, n):
        if n >= self.end:
            return None
        return self.src[n]

    def next(self):
        if self.done():
            return None
        out = self.src[self.idx]
        self.idx += 1
        return out

    def done(self):
        return self.idx >= self.end

    def emit(self, typ, val=None):
        self.tokens.append(Token(typ, val))

    def match(self, s):
        n = len(s)
        if self.peek(n) == s:
            self.idx += n
            return True

    def match_keyword(self):
        for kw in KEYWORDS:
            n = len(kw)
            if self.peek(n) == kw and not alphanumeric(self.at(self.idx+n)):
                self.match(kw)
                self.emit(TokenType(kw))
                return True
        return False

    def match_int(self):
        old_idx = self.idx
        sign = 1
        while self.peek() == '-':
            self.next()
            sign *= -1
        num = ""
        while numeric(self.peek()):
            num += self.next()
        if alpha(self.peek()) or num == "":
            self.idx = old_idx
            return False
        val = sign*int(num)
        self.emit(TokenType.INT, val)
        return True

    def match_str(self):
        if not self.match(QUOTE):
            return False
        val = ""
        while self.peek().isascii():
            if self.peek() == QUOTE and (len(val) == 0 or val[-1] is not '\\'):
                break
            val += self.next()
        if not self.match(QUOTE):
            raise ValueError
        self.emit(TokenType.STR, val)
        return True

    def match_var(self):
        if not alpha(self.peek()):
            return False
        var = ""
        while alphanumeric(self.peek()):
            var += self.next()
        self.emit(TokenType.VAR, var)
        return True

    def match_space(self):
        found_space = False
        while isspace(self.peek()):
            self.next()
            found_space = True
        return found_space

    def tokenize(self):
        if self.done():
            return None
        while not self.done():
            if self.match(TokenType.NOT_EQ.value):
                self.emit(TokenType.NOT_EQ)
            elif self.match(TokenType.LTE.value):
                self.emit(TokenType.LTE)
            elif self.match(TokenType.GTE.value):
                self.emit(TokenType.GTE)
            elif self.match(TokenType.LEFT_PAREN.value):
                self.emit(TokenType.LEFT_PAREN)
            elif self.match(TokenType.RIGHT_PAREN.value):
                self.emit(TokenType.RIGHT_PAREN)
            elif self.match(TokenType.LEFT_BRACKET.value):
                self.emit(TokenType.LEFT_BRACKET)
            elif self.match(TokenType.RIGHT_BRACKET.value):
                self.emit(TokenType.RIGHT_BRACKET)
            elif self.match(TokenType.LEFT_BRACE.value):
                self.emit(TokenType.LEFT_BRACE)
            elif self.match(TokenType.RIGHT_BRACE.value):
                self.emit(TokenType.RIGHT_BRACE)
            elif self.match(TokenType.COLON.value):
                self.emit(TokenType.COLON)
            elif self.match(TokenType.NOT.value):
                self.emit(TokenType.NOT)
            elif self.match(TokenType.AND.value):
                self.emit(TokenType.AND)
            elif self.match(TokenType.OR.value):
                self.emit(TokenType.OR)
            elif self.match(TokenType.EQ.value):
                self.emit(TokenType.EQ)
            elif self.match(TokenType.LT.value):
                self.emit(TokenType.LT)
            elif self.match(TokenType.GT.value):
                self.emit(TokenType.GT)
            elif self.match(TokenType.ADD.value):
                self.emit(TokenType.ADD)
            elif self.match_int():
                pass
            elif self.match(TokenType.SUB.value):
                self.emit(TokenType.SUB)
            elif self.match(TokenType.MUL.value):
                self.emit(TokenType.MUL)
            elif self.match(TokenType.DIV.value):
                self.emit(TokenType.DIV)
            elif self.match(TokenType.SEQ.value):
                self.emit(TokenType.SEQ)
            elif self.match_keyword():
                pass
            elif self.match_var():
                pass
            elif self.match_str():
                pass
            elif self.match_space():
                pass
            else:
                raise ValueError
        return self.tokens

##################################################################################
# Parser/AST generator
##################################################################################


class Parser(object):
    first_b = frozenset([TokenType.TRUE, TokenType.FALSE])

    first_T = frozenset([TokenType.INT, TokenType.VAR, TokenType.STR,
                         TokenType.LEFT_BRACKET, TokenType.LEFT_BRACE, TokenType.NIL]).union(first_b)

    first_UOP = frozenset([TokenType.NOT, TokenType.HEAD,
                           TokenType.TAIL, TokenType.PRINT])

    first_BOP = frozenset([
        TokenType.AND,
        TokenType.OR,
        TokenType.EQ,
        TokenType.NOT_EQ,
        TokenType.LT,
        TokenType.LTE,
        TokenType.GT,
        TokenType.GTE,
        TokenType.ADD,
        TokenType.SUB,
        TokenType.MUL,
        TokenType.DIV,
        TokenType.SEQ,
        TokenType.WHILE,
        TokenType.PUSH,
        TokenType.GET])

    first_TOP = frozenset([TokenType.IF, TokenType.PUT])

    first_E = frozenset([TokenType.LEFT_PAREN]).union(first_T)

    first_M2 = frozenset([]).union(first_E)

    first_P2 = frozenset([TokenType.VAR])

    first_L2 = frozenset([]).union(first_E)

    def __init__(self, tokens):
        self.tokens = tokens
        self.idx = 0

    def done(self):
        return self.idx >= len(self.tokens)

    def match(self, t):
        if self.done():
            raise ValueError
        out = self.tokens[self.idx]
        if out.typ != t:
            raise ValueError
        self.idx += 1
        return out

    def lookahead(self):
        if self.done():
            return None
        return self.tokens[self.idx].typ

    def E(self):
        l = self.lookahead()
        if l in self.first_T:
            e = self.T()
        elif l == TokenType.LEFT_PAREN:
            self.match(TokenType.LEFT_PAREN)
            e = self.E1()
        else:
            raise ValueError
        matched_seq = (self.lookahead() == TokenType.SEQ)
        while self.lookahead() == TokenType.SEQ:
            self.match(TokenType.SEQ)
        e2 = self.E2() if matched_seq else None
        return e if e2 is None else Seq(e, e2)

    def E1(self):
        l = self.lookahead()
        if l == TokenType.FUNC:
            self.match(TokenType.FUNC)
            v = self.v()
            p = self.P()
            self.match(TokenType.COLON)
            e = self.E()
            self.match(TokenType.RIGHT_PAREN)
            return Func(v.val, p, e, None)
        elif l == TokenType.CALL:
            self.match(TokenType.CALL)
            e = self.E()
            l = self.L()
            self.match(TokenType.RIGHT_PAREN)
            return Call(e, l)
        elif l == TokenType.LET:
            self.match(TokenType.LET)
            v = self.v()
            e = self.E()
            self.match(TokenType.RIGHT_PAREN)
            return Let(v, e)
        elif l == TokenType.MUT:
            self.match(TokenType.MUT)
            v = self.v()
            e = self.E()
            self.match(TokenType.RIGHT_PAREN)
            return Mut(v, e)
        elif l == TokenType.SET:
            self.match(TokenType.SET)
            v = self.v()
            e = self.E()
            self.match(TokenType.RIGHT_PAREN)
            return Set(v, e)
        elif l in self.first_UOP:
            uop = self.UOP()
            e = self.E()
            self.match(TokenType.RIGHT_PAREN)
            return uop(e)
        elif l in self.first_BOP:
            bop = self.BOP()
            e = self.E()
            e2 = self.E()
            self.match(TokenType.RIGHT_PAREN)
            return bop(e, e2)
        elif l in self.first_TOP:
            top = self.TOP()
            e = self.E()
            e2 = self.E()
            e3 = self.E()
            self.match(TokenType.RIGHT_PAREN)
            return top(e, e2, e3)
        elif l in self.first_E:
            e = self.E()
            self.match(TokenType.RIGHT_PAREN)
            return e
        else:
            raise ValueError

    def E2(self):
        l = self.lookahead()
        if l in self.first_E:
            e = self.E()
            return e
        else:
            return None

    def T(self):
        l = self.lookahead()
        if l == TokenType.INT:
            n = self.match(TokenType.INT)
            return Int(n.val)
        elif l in Parser.first_b:
            b = self.b()
            return Bool(b)
        elif l == TokenType.VAR:
            v = self.match(TokenType.VAR)
            return Var(v.val)
        elif l == TokenType.LEFT_BRACKET:
            self.match(TokenType.LEFT_BRACKET)
            l = self.L()
            self.match(TokenType.RIGHT_BRACKET)
            return List(l)
        elif l == TokenType.LEFT_BRACE:
            self.match(TokenType.LEFT_BRACE)
            m = self.M()
            self.match(TokenType.RIGHT_BRACE)
            return Map(m)
        elif l == TokenType.STR:
            s = self.match(TokenType.STR)
            return Str(s.val)
        elif l == TokenType.NIL:
            self.match(TokenType.NIL)
            return Nil()
        else:
            raise ValueError

    def M(self):
        l = self.lookahead()
        if l in self.first_M2:
            m2 = self.M2()
            return m2
        else:
            return {}

    def M2(self):
        k = self.E()
        self.match(TokenType.COLON)
        v = self.E()
        m = self.M()
        m[k] = v
        return m

    def P(self):
        l = self.lookahead()
        if l in self.first_P2:
            p2 = self.P2()
            return p2
        else:
            return []

    def P2(self):
        l = self.lookahead()
        if l == TokenType.VAR:
            v = self.v().val
            p = self.P()
            p.insert(0, v)
            return p
        else:
            raise ValueError

    def L(self):
        l = self.lookahead()
        if l in self.first_L2:
            l2 = self.L2()
            return l2
        else:
            return []

    def L2(self):
        e = self.E()
        l = self.L()
        l.insert(0, e)
        return l

    def UOP(self):
        l = self.lookahead()
        if l == TokenType.NOT:
            self.match(TokenType.NOT)
            return Not
        elif l == TokenType.HEAD:
            self.match(TokenType.HEAD)
            return Head
        elif l == TokenType.TAIL:
            self.match(TokenType.TAIL)
            return Tail
        elif l == TokenType.PRINT:
            self.match(TokenType.PRINT)
            return Print
        else:
            raise ValueError

    def BOP(self):
        l = self.lookahead()
        if l == TokenType.AND:
            self.match(TokenType.AND)
            return And
        elif l == TokenType.OR:
            self.match(TokenType.OR)
            return Or
        elif l == TokenType.EQ:
            self.match(TokenType.EQ)
            return Eq
        elif l == TokenType.NOT_EQ:
            self.match(TokenType.NOT_EQ)
            return NotEq
        elif l == TokenType.LT:
            self.match(TokenType.LT)
            return Lt
        elif l == TokenType.LTE:
            self.match(TokenType.LTE)
            return Lte
        elif l == TokenType.GT:
            self.match(TokenType.GT)
            return Gt
        elif l == TokenType.GTE:
            self.match(TokenType.GTE)
            return Gte
        elif l == TokenType.ADD:
            self.match(TokenType.ADD)
            return Add
        elif l == TokenType.SUB:
            self.match(TokenType.SUB)
            return Sub
        elif l == TokenType.MUL:
            self.match(TokenType.MUL)
            return Mul
        elif l == TokenType.DIV:
            self.match(TokenType.DIV)
            return Div
        elif l == TokenType.WHILE:
            self.match(TokenType.WHILE)
            return While
        elif l == TokenType.PUSH:
            self.match(TokenType.PUSH)
            return Push
        elif l == TokenType.GET:
            self.match(TokenType.GET)
            return Get
        else:
            raise ValueError

    def TOP(self):
        l = self.lookahead()
        if l == TokenType.IF:
            self.match(TokenType.IF)
            return If
        elif l == TokenType.PUT:
            self.match(TokenType.PUT)
            return Put
        else:
            raise ValueError

    def v(self):
        l = self.lookahead()
        if l == TokenType.VAR:
            v = self.match(TokenType.VAR)
            return Var(v.val)
        else:
            raise ValueError

    def b(self):
        l = self.lookahead()
        if l == TokenType.TRUE:
            self.match(TokenType.TRUE)
            return True
        elif l == TokenType.FALSE:
            self.match(TokenType.FALSE)
            return False
        else:
            raise ValueError

    def parse(self):
        if self.done():
            return None
        e = self.E()
        if not self.done():
            raise ValueError
        return e

##################################################################################
# AST types
##################################################################################


class Node(object):
    @staticmethod
    def wrap(e):
        if type(e) is int:
            return Int(e)
        elif type(e) is bool:
            return Bool(e)
        elif type(e) is str:
            return Str(e)
        else:
            return e

    @staticmethod
    def unwrap(e):
        if type(e) in [Int, Bool, Str]:
            return e.val
        else:
            return e

    def accept(self, visitor):
        pass


class BinOp(Node):
    def accept(self, visitor):
        pass


class Int(Node):
    def __init__(self, val):
        if not type(val) is int:
            raise TypeError
        self.val = val

    def __hash__(self):
        return self.val.__hash__()

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.val == other.val

    def accept(self, visitor):
        return visitor.visit_int(self)


class Add(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_add(self)


class Sub(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_sub(self)


class Mul(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_mul(self)


class Div(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_div(self)


class Eq(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_eq(self)


class NotEq(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_not_eq(self)


class Lt(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_lt(self)


class Lte(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_lte(self)


class Gt(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_gt(self)


class Gte(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_gte(self)


class Bool(Node):
    def __init__(self, val):
        if not type(val) is bool:
            raise TypeError
        self.val = val

    def __hash__(self):
        return self.val.__hash__()

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.val == other.val

    def accept(self, visitor):
        return visitor.visit_bool(self)


class And(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_and(self)


class Or(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_or(self)


class Not(Node):
    def __init__(self, arg):
        if not issubclass(type(arg), Node):
            raise TypeError
        self.arg = arg

    def accept(self, visitor):
        return visitor.visit_not(self)


class Str(Node):
    def __init__(self, val):
        if not type(val) is str:
            raise TypeError
        self.val = val

    def __hash__(self):
        return self.val.__hash__()

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.val == other.val

    def accept(self, visitor):
        return visitor.visit_str(self)


class If(Node):
    def __init__(self, cond, first, second):
        if not (issubclass(type(cond), Node) and issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.cond = cond
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_if(self)


class While(BinOp):
    def __init__(self, cond, body):
        if not (issubclass(type(cond), Node) and issubclass(type(body), Node)):
            raise TypeError
        self.cond = cond
        self.body = body

    def accept(self, visitor):
        return visitor.visit_while(self)


class Let(Node):
    # FixMe: take in a string, not a Var
    def __init__(self, var, expr):
        if not type(var) is Var:
            raise TypeError
        if not issubclass(type(expr), Node):
            raise TypeError
        self.var = var
        self.expr = expr

    def accept(self, visitor):
        return visitor.visit_let(self)


class Mut(Node):
    # FixMe: take in a string, not a Var
    def __init__(self, var, expr):
        if not type(var) is Var:
            raise TypeError
        if not issubclass(type(expr), Node):
            raise TypeError
        self.var = var
        self.expr = expr

    def accept(self, visitor):
        return visitor.visit_mut(self)


class Set(Node):
    # FixMe: take in a string, not a Var
    def __init__(self, var, expr):
        if not type(var) is Var:
            raise TypeError
        if not issubclass(type(expr), Node):
            raise TypeError
        self.var = var
        self.expr = expr

    def accept(self, visitor):
        return visitor.visit_set(self)


class Var(Node):
    def __init__(self, val):
        if not type(val) is str:
            raise TypeError
        if not (len(val) > 0 and alpha(val[0]) and alphanumeric(val)):
            raise TypeError
        self.val = val

    def accept(self, visitor):
        return visitor.visit_var(self)


class Seq(BinOp):
    def __init__(self, first, second):
        if not (issubclass(type(first), Node) and issubclass(type(second), Node)):
            raise TypeError
        self.first = first
        self.second = second

    def accept(self, visitor):
        return visitor.visit_seq(self)


class Func(Node):
    def __init__(self, name, params, body, lexical_scope):
        if not (type(name) is str or name is None):
            raise TypeError
        if not type(params) is list:
            raise TypeError
        for p in params:
            if not type(p) is str:
                raise TypeError
            if p == name:
                raise ValueError
        if not issubclass(type(body), Node):
            raise TypeError
        if not (type(lexical_scope) is Func or lexical_scope is None):
            raise TypeError
        self.name = name
        self.params = params
        self.body = body
        self.env = {}
        self.lexical_scope = lexical_scope

    def accept(self, visitor):
        return visitor.visit_func(self)


class Call(Node):
    def __init__(self, func, args):
        if not issubclass(type(func), Node):
            raise TypeError
        if not type(args) is list:
            raise TypeError
        for a in args:
            if not issubclass(type(a), Node):
                raise TypeError
        self.func = func
        self.args = args

    def accept(self, visitor):
        return visitor.visit_call(self)


class Map(Node):
    def __init__(self, mappings):
        if not type(mappings) is dict:
            raise TypeError
        for k, v in mappings.items():
            if not (issubclass(type(k), Node) and issubclass(type(v), Node)):
                raise TypeError
        self.mappings = mappings

    def accept(self, visitor):
        return visitor.visit_map(self)

    def __str__(self):
        return Printer()(self)

    def __bool__(self):
        return len(self.mappings) != 0


class Get(Node):
    def __init__(self, a, k):
        if not (issubclass(type(a), Node) and issubclass(type(k), Node)):
            raise TypeError
        self.a = a
        self.k = k

    def accept(self, visitor):
        return visitor.visit_get(self)


class Put(Node):
    def __init__(self, a, k, v):
        if not (issubclass(type(a), Node) and issubclass(type(k), Node) and issubclass(type(v), Node)):
            raise TypeError
        self.a = a
        self.k = k
        self.v = v

    def accept(self, visitor):
        return visitor.visit_put(self)


class List(Node):
    def __init__(self, elements):
        if not type(elements) is list:
            raise TypeError
        for e in elements:
            if not issubclass(type(e), Node):
                raise TypeError
        self.elements = elements

    def accept(self, visitor):
        return visitor.visit_list(self)

    def __str__(self):
        return Printer()(self)

    def __bool__(self):
        return len(self.elements) != 0


class Head(Node):
    def __init__(self, arg):
        if not issubclass(type(arg), Node):
            raise TypeError
        self.arg = arg

    def accept(self, visitor):
        return visitor.visit_head(self)


class Tail(Node):
    def __init__(self, arg):
        if not issubclass(type(arg), Node):
            raise TypeError
        self.arg = arg

    def accept(self, visitor):
        return visitor.visit_tail(self)


class Push(BinOp):
    def __init__(self, head, tail):
        if not (issubclass(type(head), Node) and issubclass(type(tail), Node)):
            raise TypeError
        self.head = head
        self.tail = tail

    def accept(self, visitor):
        return visitor.visit_push(self)


class Print(Node):
    def __init__(self, arg):
        if not issubclass(type(arg), Node):
            raise TypeError
        self.arg = arg

    def accept(self, visitor):
        return visitor.visit_print(self)


class Nil(Node):
    # FixMe: make singleton
    def __init__(self):
        pass

    def __str__(self):
        return TokenType.NIL.value

    def accept(self, visitor):
        return visitor.visit_nil(self)

##################################################################################
# Visitor base class
##################################################################################


class Visitor(object):
    def __call__(self, node):
        return node.accept(self)

    def visit_int(self, node):
        raise NotImplementedError

    def visit_add(self, node):
        raise NotImplementedError

    def visit_mul(self, node):
        raise NotImplementedError

    def visit_div(self, node):
        raise NotImplementedError

    def visit_eq(self, node):
        raise NotImplementedError

    def visit_not_eq(self, node):
        raise NotImplementedError

    def visit_lt(self, node):
        raise NotImplementedError

    def visit_lte(self, node):
        raise NotImplementedError

    def visit_gt(self, node):
        raise NotImplementedError

    def visit_gte(self, node):
        raise NotImplementedError

    def visit_bool(self, node):
        raise NotImplementedError

    def visit_and(self, node):
        raise NotImplementedError

    def visit_or(self, node):
        raise NotImplementedError

    def visit_if(self, node):
        raise NotImplementedError

    def visit_not(self, node):
        raise NotImplementedError

    def visit_str(self, node):
        raise NotImplementedError

    def visit_while(self, node):
        raise NotImplementedError

    def visit_let(self, node):
        raise NotImplementedError

    def visit_mut(self, node):
        raise NotImplementedError

    def visit_var(self, node):
        raise NotImplementedError

    def visit_seq(self, node):
        raise NotImplementedError

    def visit_func(self, node):
        raise NotImplementedError

    def visit_call(self, node):
        raise NotImplementedError

    def visit_map(self, node):
        raise NotImplementedError

    def visit_get(self, node):
        raise NotImplementedError

    def visit_put(self, node):
        raise NotImplementedError

    def visit_list(self, node):
        raise NotImplementedError

    def visit_head(self, node):
        raise NotImplementedError

    def vist_tail(self, node):
        raise NotImplementedError

    def visit_push(self, node):
        raise NotImplementedError

    def visit_print(self, node):
        raise NotImplementedError

    def visit_nil(self, node):
        raise NotImplementedError

##################################################################################
# AST printer
##################################################################################


class Printer(Visitor):
    def __init__(self):
        self.indent = ""

    def visit_int(self, node):
        if not type(node) is Int:
            raise TypeError
        return str(node.val)

    def visit_add(self, node):
        if not type(node) is Add:
            raise TypeError
        return "(%s %s %s)" % (TokenType.ADD.value, self(node.first), self(node.second))

    def visit_sub(self, node):
        if not type(node) is Sub:
            raise TypeError
        return "(%s %s %s)" % (TokenType.SUB.value, self(node.first), self(node.second))

    def visit_mul(self, node):
        if not type(node) is Mul:
            raise TypeError
        return "(%s %s %s)" % (TokenType.MUL.value, self(node.first), self(node.second))

    def visit_div(self, node):
        if not type(node) is Div:
            raise TypeError
        return "(%s %s %s)" % (TokenType.DIV.value, self(node.first), self(node.second))

    def visit_eq(self, node):
        if not type(node) is Eq:
            raise TypeError
        return "(%s %s %s)" % (TokenType.EQ.value, self(node.first), self(node.second))

    def visit_not_eq(self, node):
        if not type(node) is NotEq:
            raise TypeError
        return "(%s %s %s)" % (TokenType.NOT_EQ.value, self(node.first), self(node.second))

    def visit_lt(self, node):
        if not type(node) is Lt:
            raise TypeError
        return "(%s %s %s)" % (TokenType.LT.value, self(node.first), self(node.second))

    def visit_lte(self, node):
        if not type(node) is Lte:
            raise TypeError
        return "(%s %s %s)" % (TokenType.LTE.value, self(node.first), self(node.second))

    def visit_gt(self, node):
        if not type(node) is Gt:
            raise TypeError
        return "(%s %s %s)" % (TokenType.GT.value, self(node.first), self(node.second))

    def visit_gte(self, node):
        if not type(node) is Gte:
            raise TypeError
        return "(%s %s %s)" % (TokenType.GTE.value, self(node.first), self(node.second))

    def visit_bool(self, node):
        if not type(node) is Bool:
            raise TypeError
        return str(node.val)

    def visit_and(self, node):
        if not type(node) is And:
            raise TypeError
        return "(%s %s %s)" % (TokenType.AND.value, self(node.first), self(node.second))

    def visit_or(self, node):
        if not type(node) is Or:
            raise TypeError
        return "(%s %s %s)" % (TokenType.OR.value, self(node.first), self(node.second))

    def visit_if(self, node):
        if not type(node) is If:
            raise TypeError
        cond = self(node.cond)
        indent = self.indent
        self.indent = indent + "  "
        tbranch = self(node.first)
        self.indent = indent + "  "
        fbranch = self(node.second)
        self.indent = indent
        return (TokenType.LEFT_PAREN.value + TokenType.IF.value + ' ' + cond +
                '\n' + indent + '  ' + tbranch +
                '\n' + indent + '  ' + fbranch +
                '\n' + indent + TokenType.RIGHT_PAREN.value)

    def visit_not(self, node):
        if not type(node) is Not:
            raise TypeError
        return '%s%s' % (TokenType.NOT.value, self(node.arg))

    def visit_str(self, node):
        if not type(node) is Str:
            raise TypeError
        return "%s%s%s" % (QUOTE, node.val, QUOTE)

    def visit_while(self, node):
        if not type(node) is While:
            raise TypeError
        cond = self(node.cond)
        indent = self.indent
        self.indent = indent + "  "
        body = self(node.body)
        self.indent = indent
        return (TokenType.LEFT_PAREN.value + TokenType.WHILE.value + cond +
                '\n' + indent + '  ' + body +
                '\n' + indent + TokenType.RIGHT_PAREN.value)

    def visit_let(self, node):
        if not type(node) is Let:
            raise TypeError
        return "(%s %s %s)" % (TokenType.LET.value, self(node.var), self(node.expr))

    def visit_mut(self, node):
        if not type(node) is Mut:
            raise TypeError
        return "(%s %s %s)" % (TokenType.MUT.value, self(node.var), self(node.expr))

    def visit_set(self, node):
        if not type(node) is Set:
            raise TypeError
        return "(%s %s %s)" % (TokenType.SET.value, self(node.var), self(node.expr))

    def visit_var(self, node):
        if not type(node) is Var:
            raise TypeError
        return node.val

    def visit_seq(self, node):
        if not type(node) is Seq:
            raise TypeError
        return "%s%s\n%s%s" % (self(node.first), TokenType.SEQ.value, self.indent, self(node.second))

    def visit_func(self, node):
        if not type(node) is Func:
            raise TypeError
        params = " " + " ".join(node.params) if len(node.params) > 0 else ""
        indent = self.indent
        self.indent = indent + "  "
        body = self(node.body)
        self.indent = indent
        return (TokenType.LEFT_PAREN.value + TokenType.FUNC.value + ' ' + node.name + params + TokenType.COLON.value +
                '\n' + indent + '  ' + body +
                '\n' + indent + TokenType.RIGHT_PAREN.value)

    def visit_call(self, node):
        if not type(node) is Call:
            raise TypeError
        args = " " + " ".join([self(a) for a in node.args]
                              ) if len(node.args) > 0 else ""
        return (TokenType.LEFT_PAREN.value + TokenType.CALL.value + ' ' + self(node.func) + args +
                TokenType.RIGHT_PAREN.value)

    def visit_map(self, node):
        if not type(node) is Map:
            raise TypeError
        if len(node.mappings) == 0:
            return TokenType.LEFT_BRACE.value + TokenType.RIGHT_BRACE.value
        indent = self.indent
        self.indent = indent + "  "
        mappings = ("\n" + self.indent).join(
            [("%s%s%s" % (self(k), TokenType.COLON.value, self(node.mappings[k]))) for k in node.mappings])
        self.indent = indent
        return TokenType.LEFT_BRACE.value + "\n" + self.indent + "  " + mappings + "\n" + self.indent + TokenType.RIGHT_BRACE.value

    def visit_get(self, node):
        if not type(node) is Get:
            raise TypeError
        return (TokenType.LEFT_PAREN.value + TokenType.GET.value + " " + self(node.a) + " " + self(node.k) +
                TokenType.RIGHT_PAREN.value)

    def visit_put(self, node):
        if not type(node) is Put:
            raise TypeError
        return (TokenType.LEFT_PAREN.value + TokenType.PUT.value + " " + self(node.a) + " " + self(node.k) + " " +
                self(node.v) + TokenType.RIGHT_PAREN.value)

    def visit_list(self, node):
        if not type(node) is List:
            raise TypeError
        elements = " ".join([self(e) for e in node.elements]) if len(
            node.elements) > 0 else ""
        return TokenType.LEFT_BRACKET.value + elements + TokenType.RIGHT_BRACKET.value

    def visit_head(self, node):
        if not type(node) is Head:
            raise TypeError
        return (TokenType.LEFT_PAREN.value + TokenType.HEAD.value + " " + self(node.arg) +
                TokenType.RIGHT_PAREN.value)

    def visit_tail(self, node):
        if not type(node) is Tail:
            raise TypeError
        return (TokenType.LEFT_PAREN.value + TokenType.TAIL.value + " " + self(node.arg) +
                TokenType.RIGHT_PAREN.value)

    def visit_push(self, node):
        if not type(node) is Push:
            raise TypeError
        return (TokenType.LEFT_PAREN.value + TokenType.PUSH.value + " " + self(node.head) + " " +
                self(node.tail) + TokenType.RIGHT_PAREN.value)

    def visit_print(self, node):
        if not type(node) is Print:
            raise TypeError
        return (TokenType.LEFT_PAREN.value + TokenType.PRINT.value + " " + self(node.arg) +
                TokenType.RIGHT_PAREN.value)

    def visit_nil(self, node):
        if not type(node) is Nil:
            raise TypeError
        return TokenType.NIL.value

##################################################################################
# AST evaluator
##################################################################################


@enum.unique
class Scope(enum.Enum):
    PARAM = enum.auto()
    LOCAL = enum.auto()
    INHERITED = enum.auto()


@enum.unique
class Decl(enum.Enum):
    LET = enum.auto()
    MUT = enum.auto()
    NONE = enum.auto()  # used for set <var> <val>


class Binding(object):
    def __init__(self, scope, decl, is_current_func, val):
        if type(scope) is not Scope:
            raise TypeError
        if type(decl) is not Decl:
            raise TypeError
        if type(is_current_func) is not bool:
            raise TypeError
        self.scope = scope
        self.decl = decl
        self.is_current_func = is_current_func
        self.val = val


class Frame(object):
    def __init__(self, func, env):
        if not (type(func) is Func or func is None):
            raise TypeError
        if not type(env) is dict:
            raise TypeError
        self.func = func
        self.env = env


class Evaluator(Visitor):
    def __init__(self):
        self.stack = [Frame(None, {})]

    def current_frame(self):
        return self.stack[-1]

    def read(self, name, frame=None):
        if type(name) is not str:
            raise TypeError
        frame = self.current_frame() if frame is None else frame
        if name in frame.env:
            return frame.env[name]
        return None

    def write(self, name, binding, frame=None):
        if type(name) is not str:
            raise TypeError
        frame = self.current_frame() if frame is None else frame
        current_binding = frame.env.get(name, None)
        if current_binding is None:
            frame.env[name] = binding
        elif current_binding.scope == Scope.LOCAL:
            if binding.decl in [Decl.LET, Decl.MUT]:
                raise ValueError(
                    "re-declaration of %s inside local scope" % name)
            elif current_binding.decl == Decl.LET:
                raise ValueError("cannot rebind non-mutable %s" % name)
            else:
                frame.env[name] = binding
        elif current_binding.scope == Scope.INHERITED:
            if current_binding.is_current_func:
                raise ValueError(
                    "re-binding of current function %s" % name)
            elif binding.decl in [Decl.LET, Decl.MUT]:
                frame.env[name] = binding
            elif current_binding.decl == Decl.LET:
                raise ValueError("cannot rebind non-mutable %s" % name)
            else:
                frame.env[name] = binding
        elif current_binding.scope == Scope.PARAM:
            if binding.decl in [Decl.LET, Decl.MUT]:
                raise ValueError("re-declaration of param %s" % name)
            elif current_binding.decl == Decl.MUT:
                raise ValueError("cannot rebind non-mutable %s" % name)
            else:
                raise AssertionError("found mutable param %s" % name)
        else:
            raise AssertionError("unknown scope type %s" %
                                 str(current_binding.scope))

    def visit_int(self, node):
        if not type(node) is Int:
            raise TypeError
        return node.val

    def visit_add(self, node):
        if not type(node) is Add:
            raise TypeError
        return self(node.first) + self(node.second)

    def visit_sub(self, node):
        if not type(node) is Sub:
            raise TypeError
        return self(node.first) - self(node.second)

    def visit_mul(self, node):
        if not type(node) is Mul:
            raise TypeError
        return self(node.first) * self(node.second)

    def visit_div(self, node):
        if not type(node) is Div:
            raise TypeError
        return int(self(node.first) / self(node.second))

    def visit_eq(self, node):
        if not type(node) is Eq:
            raise TypeError
        return self(node.first) == self(node.second)

    def visit_not_eq(self, node):
        if not type(node) is NotEq:
            raise TypeError
        return self(node.first) != self(node.second)

    def visit_lt(self, node):
        if not type(node) is Lt:
            raise TypeError
        return self(node.first) < self(node.second)

    def visit_lte(self, node):
        if not type(node) is Lte:
            raise TypeError
        return self(node.first) <= self(node.second)

    def visit_gt(self, node):
        if not type(node) is Gt:
            raise TypeError
        return self(node.first) > self(node.second)

    def visit_gte(self, node):
        if not type(node) is Gte:
            raise TypeError
        return self(node.first) >= self(node.second)

    def visit_bool(self, node):
        if not type(node) is Bool:
            raise TypeError
        return node.val

    def visit_and(self, node):
        if not type(node) is And:
            raise TypeError
        return self(node.first) and self(node.second)

    def visit_or(self, node):
        if not type(node) is Or:
            raise TypeError
        return self(node.first) or self(node.second)

    def visit_not(self, node):
        if not type(node) is Not:
            raise TypeError
        return not self(node.arg)

    def visit_str(self, node):
        if not type(node) is Str:
            raise TypeError
        return json.loads('%s%s%s' % (QUOTE, node.val, QUOTE))

    def visit_if(self, node):
        if not type(node) is If:
            raise TypeError
        return self(node.first) if self(node.cond) else self(node.second)

    def visit_while(self, node):
        if not type(node) is While:
            raise TypeError
        out = False
        while(self(node.cond)):
            out = self(node.body)
        return out

    def visit_let(self, node):
        if not type(node) is Let:
            raise TypeError
        val = self(node.expr)
        binding = Binding(Scope.LOCAL, Decl.LET, False, val)
        self.write(node.var.val, binding)
        return val

    def visit_mut(self, node):
        if not type(node) is Mut:
            raise TypeError
        val = self(node.expr)
        binding = Binding(Scope.LOCAL, Decl.MUT, False, val)
        self.write(node.var.val, binding)
        return val

    def visit_set(self, node):
        if not type(node) is Set:
            raise TypeError
        binding = self.read(node.var.val)
        if binding is None:
            raise ValueError
        val = self(node.expr)
        binding = Binding(binding.scope, Decl.NONE, False, val)
        self.write(node.var.val, binding)
        # Propagate write up call stack as long as the calling context is the same as the lexical
        # scope, as is the case when nested functions are called within their enclosing lexical
        # scope. Note that the lexical scope can be different from the calling context, e.g.
        # when a nested function is returned and subsequently called outside of its lexical scope;
        # in this case, no propagation is necessary.
        func = self.current_frame().func
        idx = -2  # FixMe: clean up
        while binding.scope == Scope.INHERITED and func and func.lexical_scope == self.stack[idx].func:
            binding = self.read(node.var.val, self.stack[idx])
            binding.val = val
            func = func.lexical_scope
            idx -= 1
        return val

    def visit_var(self, node):
        if not type(node) is Var:
            raise TypeError
        binding = self.read(node.val)
        if binding is None:
            raise ValueError
        return binding.val

    def visit_seq(self, node):
        if not type(node) is Seq:
            raise TypeError
        self(node.first)
        return self(node.second)

    def visit_func(self, node):
        if not type(node) is Func:
            raise TypeError
        out = Func(node.name, node.params, node.body,
                   self.current_frame().func)
        out.env = {}
        for name, binding in self.current_frame().env.items():
            out.env[name] = Binding(
                Scope.INHERITED, binding.decl, False, binding.val)
        out.env[out.name] = Binding(Scope.INHERITED, Decl.LET, False, out)
        self.write(out.name, out.env[out.name])
        return out

    def visit_call(self, node):
        if not type(node) is Call:
            raise TypeError
        func = self(node.func)
        if not type(func) is Func:
            raise TypeError
        if len(func.params) < len(node.args):
            raise ValueError
        if len(func.params) == len(node.args):
            # All params available - evaluate the function
            env = {}
            for name, binding in func.env.items():
                env[name] = Binding(
                    binding.scope, binding.decl, False, binding.val)
            for i, a in enumerate(node.args):
                name = func.params[i]
                env[name] = Binding(Scope.PARAM, Decl.LET, False, self(a))
            env[func.name] = Binding(Scope.INHERITED, Decl.LET, True, func)
            self.stack.append(Frame(func, env))
            out = self(func.body)
            self.stack.pop()
        else:
            # Not all params available - return a closure
            params = [p for p in func.params[len(node.args):]]
            out = Func(func.name, params, func.body, func.lexical_scope)
            for name, binding in func.env.items():
                out.env[name] = Binding(
                    binding.scope, binding.decl, False, binding.val)
            for i, a in enumerate(node.args):
                name = func.params[i]
                out.env[name] = Binding(Scope.PARAM, Decl.LET, False, self(a))
        return out

    def visit_map(self, node):
        if not type(node) is Map:
            raise TypeError
        mappings = {}
        for k, v in node.mappings.items():
            mappings[Node.wrap(self(k))] = Node.wrap(self(v))
        return Map(mappings)

    def visit_get(self, node):
        if not type(node) is Get:
            raise TypeError
        a = self(node.a)
        if not type(a) is Map:
            raise TypeError
        k = Node.wrap(self(node.k))
        if k not in a.mappings:
            raise KeyError
        v = a.mappings[k]
        return self(v)

    def visit_put(self, node):
        if not type(node) is Put:
            raise TypeError
        a = self(node.a)
        if not type(a) is Map:
            raise TypeError
        k = Node.wrap(self(node.k))
        v = Node.wrap(self(node.v))
        a.mappings[k] = v
        return a
        # FixMe: too slow. For now, maps will be mutable
        #mappings = copy.copy(a.mappings)
        #mappings[k] = v
        # return Map(mappings)

    def visit_list(self, node):
        if not type(node) is List:
            raise TypeError
        return List([Node.wrap(self(e)) for e in node.elements])

    def visit_head(self, node):
        if not type(node) is Head:
            raise TypeError
        l = self(node.arg)
        if not type(l) is List:
            raise TypeError
        if len(l.elements) <= 0:
            raise ValueError
        h = l.elements[0]
        return self(h)

    def visit_tail(self, node):
        if not type(node) is Tail:
            raise TypeError
        l = self(node.arg)
        if not type(l) is List:
            raise TypeError
        if len(l.elements) <= 0:
            raise ValueError
        tail = l.elements[1:]
        return List(tail)

    def visit_push(self, node):
        if not type(node) is Push:
            raise TypeError
        l = self(node.tail)
        if not type(l) is List:
            raise TypeError
        tail = l.elements
        head = Node.wrap(self(node.head))
        return List([head] + tail)

    def visit_print(self, node):
        if not type(node) is Print:
            raise TypeError
        print(self(node.arg))
        return Nil()

    def visit_nil(self, node):
        if not type(node) is Nil:
            raise TypeError
        return node

##################################################################################
# AST type checker
##################################################################################


class TypeChecker(Visitor):
    # FixMe: implement
    pass

##################################################################################
# Interpreter
##################################################################################


class Interpreter(object):
    def __init__(self, src):
        self.src = src

    def interpret(self, verbose=False):
        tokens = Tokenizer(self.src).tokenize()
        ast = Parser(tokens).parse()
        if verbose:
            print("\n*********************")
            print("Parsed the following:")
            print("*********************")
            print(Printer()(ast))
            print("*********************\n")
        res = Evaluator()(ast)
        return res
