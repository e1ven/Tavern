from Cython.Compiler.Visitor import TreeVisitor
from Cython.Compiler.Nodes import *
from Cython.Compiler.ExprNodes import *

"""
Serializes a Cython code tree to Cython code. This is primarily useful for
debugging and testing purposes.

The output is in a strict format, no whitespace or comments from the input
is preserved (and it could not be as it is not present in the code tree).
"""

class LinesResult(object):
    def __init__(self):
        self.lines = []
        self.s = ""

    def put(self, s):
        self.s += s

    def newline(self):
        self.lines.append(self.s)
        self.s = ""

    def putline(self, s):
        self.put(s)
        self.newline()

class DeclarationWriter(TreeVisitor):

    indent_string = "    "

    def __init__(self, result = None):
        super(DeclarationWriter, self).__init__()
        if result is None:
            result = LinesResult()
        self.result = result
        self.numindents = 0
        self.tempnames = {}
        self.tempblockindex = 0

    def write(self, tree):
        self.visit(tree)
        return self.result

    def indent(self):
        self.numindents += 1

    def dedent(self):
        self.numindents -= 1

    def startline(self, s = ""):
        self.result.put(self.indent_string * self.numindents + s)

    def put(self, s):
        self.result.put(s)

    def putline(self, s):
        self.result.putline(self.indent_string * self.numindents + s)

    def endline(self, s = ""):
        self.result.putline(s)

    def line(self, s):
        self.startline(s)
        self.endline()

    def comma_separated_list(self, items, output_rhs=False):
        if len(items) > 0:
            for item in items[:-1]:
                self.visit(item)
                if output_rhs and item.default is not None:
                    self.put(" = ")
                    self.visit(item.default)
                self.put(", ")
            self.visit(items[-1])

    def visit_Node(self, node):
        raise AssertionError("Node not handled by serializer: %r" % node)

    def visit_ModuleNode(self, node):
        self.visitchildren(node)

    def visit_StatListNode(self, node):
        self.visitchildren(node)
    
    def visit_CDefExternNode(self, node):
        if node.include_file is None:
            file = '*'
        else:
            file = '"%s"' % node.include_file
        self.putline("cdef extern from %s:" % file)
        self.indent()
        self.visit(node.body)
        self.dedent()

    def visit_CPtrDeclaratorNode(self, node):
        self.put('*')
        self.visit(node.base)

    def visit_CReferenceDeclaratorNode(self, node):
        self.put('&')
        self.visit(node.base)

    def visit_CArrayDeclaratorNode(self, node):
        self.visit(node.base)
        self.put('[')
        if node.dimension is not None:
            self.visit(node.dimension)
        self.put(']')

    def visit_CArrayDeclaratorNode(self, node):
        self.visit(node.base)
        self.put('[')
        if node.dimension is not None:
            self.visit(node.dimension)
        self.put(']')

    def visit_CFuncDeclaratorNode(self, node):
        # TODO: except, gil, etc.
        self.visit(node.base)
        self.put('(')
        self.comma_separated_list(node.args)
        self.endline(')')

    def visit_CNameDeclaratorNode(self, node):
        self.put(node.name)

    def visit_CSimpleBaseTypeNode(self, node):
        # See Parsing.p_sign_and_longness
        if node.is_basic_c_type:
            self.put(("unsigned ", "", "signed ")[node.signed])
            if node.longness < 0:
                self.put("short " * -node.longness)
            elif node.longness > 0:
                self.put("long " * node.longness)
        self.put(node.name)

    def visit_CComplexBaseTypeNode(self, node):
        self.put('(')
        self.visit(node.base_type)
        self.visit(node.declarator)
        self.put(')')

    def visit_CNestedBaseTypeNode(self, node):
        self.visit(node.base_type)
        self.put('.')
        self.put(node.name)

    def visit_TemplatedTypeNode(self, node):
        self.visit(node.base_type_node)
        self.put('[')
        self.comma_separated_list(node.positional_args + node.keyword_args.key_value_pairs)
        self.put(']')

    def visit_CVarDefNode(self, node):
        self.startline("cdef ")
        self.visit(node.base_type)
        self.put(" ")
        self.comma_separated_list(node.declarators, output_rhs=True)
        self.endline()

    def visit_container_node(self, node, decl, extras, attributes):
        # TODO: visibility
        self.startline(decl)
        if node.name:
            self.put(' ')
            self.put(node.name)
            if node.cname is not None:
                self.put(' "%s"' % node.cname)
        if extras:
            self.put(extras)
        self.endline(':')
        self.indent()
        if not attributes:
            self.putline('pass')
        else:
            for attribute in attributes:
                self.visit(attribute)
        self.dedent()

    def visit_CStructOrUnionDefNode(self, node):
        if node.typedef_flag:
            decl = 'ctypedef '
        else:
            decl = 'cdef '
        if node.visibility == 'public':
            decl += 'public '
        if node.packed:
            decl += 'packed '
        decl += node.kind
        self.visit_container_node(node, decl, None, node.attributes)

    def visit_CppClassNode(self, node):
        extras = ""
        if node.templates:
            extras = "[%s]" % ", ".join(node.templates)
        if node.base_classes:
            extras += "(%s)" % ", ".join(node.base_classes)
        self.visit_container_node(node, "cdef cppclass", extras, node.attributes)

    def visit_CEnumDefNode(self, node):
        self.visit_container_node(node, "cdef enum", None, node.items)

    def visit_CEnumDefItemNode(self, node):
        self.startline(node.name)
        if node.cname:
            self.put(' "%s"' % node.cname)
        if node.value:
            self.put(" = ")
            self.visit(node.value)
        self.endline()

    def visit_CClassDefNode(self, node):
        assert not node.module_name
        if node.decorators:
            for decorator in node.decorators:
                self.visit(decorator)
        self.startline("cdef class ")
        self.put(node.class_name)
        if node.base_class_name:
            self.put("(")
            if node.base_class_module:
                self.put(node.base_class_module)
                self.put(".")
            self.put(node.base_class_name)
            self.put(")")
        self.endline(":")
        self.indent()
        self.visit(node.body)
        self.dedent()

    def visit_CTypeDefNode(self, node):
        self.startline("ctypedef ")
        self.visit(node.base_type)
        self.put(" ")
        self.visit(node.declarator)
        self.endline()

    def visit_FuncDefNode(self, node):
        self.startline("def %s(" % node.name)
        self.comma_separated_list(node.args)
        self.endline("):")
        self.indent()
        self.visit(node.body)
        self.dedent()

    def visit_CArgDeclNode(self, node):
        if node.base_type.name is not None:
            self.visit(node.base_type)
            self.put(" ")
        self.visit(node.declarator)
        if node.default is not None:
            self.put(" = ")
            self.visit(node.default)

    def visit_CImportStatNode(self, node):
        self.startline("cimport ")
        self.put(node.module_name)
        if node.as_name:
            self.put(" as ")
            self.put(node.as_name)
        self.endline()

    def visit_FromCImportStatNode(self, node):
        self.startline("from ")
        self.put(node.module_name)
        self.put(" cimport ")
        first = True
        for pos, name, as_name, kind in node.imported_names:
            assert kind is None
            if first:
                first = False
            else:
                self.put(", ")
            self.put(name)
            if as_name:
                self.put(" as ")
                self.put(as_name)
        self.endline()

    def visit_NameNode(self, node):
        self.put(node.name)

    def visit_IntNode(self, node):
        self.put(node.value)

    def visit_NoneNode(self, node):
        self.put("None")

    def visit_NotNode(self, node):
        self.put("(not ")
        self.visit(node.operand)
        self.put(")")

    def visit_DecoratorNode(self, node):
        self.startline("@")
        self.visit(node.decorator)
        self.endline()

    def visit_BinopNode(self, node):
        self.visit(node.operand1)
        self.put(" %s " % node.operator)
        self.visit(node.operand2)

    def visit_AttributeNode(self, node):
        self.visit(node.obj)
        self.put(".%s" % node.attribute)

    def visit_BoolNode(self, node):
        self.put(str(node.value))

    # FIXME: represent string nodes correctly
    def visit_StringNode(self, node):
        value = node.value
        if value.encoding is not None:
            value = value.encode(value.encoding)
        self.put(repr(value))

    def visit_PassStatNode(self, node):
        self.startline("pass")
        self.endline()

class CodeWriter(DeclarationWriter):

    def visit_SingleAssignmentNode(self, node):
        self.startline()
        self.visit(node.lhs)
        self.put(" = ")
        self.visit(node.rhs)
        self.endline()

    def visit_CascadedAssignmentNode(self, node):
        self.startline()
        for lhs in node.lhs_list:
            self.visit(lhs)
            self.put(" = ")
        self.visit(node.rhs)
        self.endline()

    def visit_PrintStatNode(self, node):
        self.startline("print ")
        self.comma_separated_list(node.arg_tuple.args)
        if not node.append_newline:
            self.put(",")
        self.endline()

    def visit_ForInStatNode(self, node):
        self.startline("for ")
        self.visit(node.target)
        self.put(" in ")
        self.visit(node.iterator.sequence)
        self.endline(":")
        self.indent()
        self.visit(node.body)
        self.dedent()
        if node.else_clause is not None:
            self.line("else:")
            self.indent()
            self.visit(node.else_clause)
            self.dedent()

    def visit_IfStatNode(self, node):
        # The IfClauseNode is handled directly without a seperate match
        # for clariy.
        self.startline("if ")
        self.visit(node.if_clauses[0].condition)
        self.endline(":")
        self.indent()
        self.visit(node.if_clauses[0].body)
        self.dedent()
        for clause in node.if_clauses[1:]:
            self.startline("elif ")
            self.visit(clause.condition)
            self.endline(":")
            self.indent()
            self.visit(clause.body)
            self.dedent()
        if node.else_clause is not None:
            self.line("else:")
            self.indent()
            self.visit(node.else_clause)
            self.dedent()

    def visit_SequenceNode(self, node):
        self.comma_separated_list(node.args) # Might need to discover whether we need () around tuples...hmm...

    def visit_SimpleCallNode(self, node):
        self.visit(node.function)
        self.put("(")
        self.comma_separated_list(node.args)
        self.put(")")

    def visit_GeneralCallNode(self, node):
        self.visit(node.function)
        self.put("(")
        posarg = node.positional_args
        if isinstance(posarg, AsTupleNode):
            self.visit(posarg.arg)
        else:
            self.comma_separated_list(posarg)
        if node.keyword_args is not None or node.starstar_arg is not None:
            raise Exception("Not implemented yet")
        self.put(")")

    def visit_ExprStatNode(self, node):
        self.startline()
        self.visit(node.expr)
        self.endline()

    def visit_InPlaceAssignmentNode(self, node):
        self.startline()
        self.visit(node.lhs)
        self.put(" %s= " % node.operator)
        self.visit(node.rhs)
        self.endline()

    def visit_WithStatNode(self, node):
        self.startline()
        self.put("with ")
        self.visit(node.manager)
        if node.target is not None:
            self.put(" as ")
            self.visit(node.target)
        self.endline(":")
        self.indent()
        self.visit(node.body)
        self.dedent()

    def visit_TryFinallyStatNode(self, node):
        self.line("try:")
        self.indent()
        self.visit(node.body)
        self.dedent()
        self.line("finally:")
        self.indent()
        self.visit(node.finally_clause)
        self.dedent()

    def visit_TryExceptStatNode(self, node):
        self.line("try:")
        self.indent()
        self.visit(node.body)
        self.dedent()
        for x in node.except_clauses:
            self.visit(x)
        if node.else_clause is not None:
            self.visit(node.else_clause)

    def visit_ExceptClauseNode(self, node):
        self.startline("except")
        if node.pattern is not None:
            self.put(" ")
            self.visit(node.pattern)
        if node.target is not None:
            self.put(", ")
            self.visit(node.target)
        self.endline(":")
        self.indent()
        self.visit(node.body)
        self.dedent()

    def visit_ReturnStatNode(self, node):
        self.startline("return ")
        self.visit(node.value)
        self.endline()

    def visit_ReraiseStatNode(self, node):
        self.line("raise")

    def visit_ImportNode(self, node):
        self.put("(import %s)" % node.module_name.value)

    def visit_TempsBlockNode(self, node):
        """
        Temporaries are output like $1_1', where the first number is
        an index of the TempsBlockNode and the second number is an index
        of the temporary which that block allocates.
        """
        idx = 0
        for handle in node.temps:
            self.tempnames[handle] = "$%d_%d" % (self.tempblockindex, idx)
            idx += 1
        self.tempblockindex += 1
        self.visit(node.body)

    def visit_TempRefNode(self, node):
        self.put(self.tempnames[node.handle])


class PxdWriter(DeclarationWriter):
    def __call__(self, node):
        print('\n'.join(self.write(node).lines))
        return node

    def visit_CFuncDefNode(self, node):
        if 'inline' in node.modifiers:
            return
        if node.overridable:
            self.startline('cpdef ')
        else:
            self.startline('cdef ')
        if node.visibility != 'private':
            self.put(node.visibility)
            self.put(' ')
        if node.api:
            self.put('api ')
        self.visit(node.declarator)
    
    def visit_StatNode(self, node):
        pass

    