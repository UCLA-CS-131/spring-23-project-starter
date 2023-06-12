"""
# v3
- templated classes
. (template_class foo (type1 type2 .. typen) (method ...) (field ...) ...)
. check for proper # of types specified during instantiation of the template
. when instantiating:
  (new foo@type1@type2@...@typen)

- default field and local variables

- exceptions
. new throw keyword, always throws a string: (throw "string")
* new try keyword: (try (statement) (catch-statement))
* a string variable named "exception" will be added to the environment of the exception statement, and have its
  scope limited to that block.
. add new status type: STATUS_EXCEPTION, and return exception text in second value of tuple
. update call_method to return status and return value (not just return value)
. update while loop
. update begin
. update let

test for exceptions:
* non string thrown
"""

# """ Things to document
# . no inheritance from or by templated classes
# . no recursive definitions, e.g., map<list<int>>
# . variable names, class names, nor function names may have @ characters in them
# . main class can't be templated
# . any expression that creatse a string to be thrown can't throw an exception
# . there may not be a variable named exception defined by the user and we won't test with this
# """


import copy
from intbase import InterpreterBase, ErrorType
from type_valuev3 import Type, create_value, create_default_value


class VariableDef:
    # var_type is a Type() and value is a Value()
    def __init__(self, var_type, var_name, value=None):
        self.type = var_type
        self.name = var_name
        self.value = value

    def set_value(self, value):
        self.value = value


# parses and holds the definition of a member method
# [method return_type method_name [[type1 param1] [type2 param2] ...] [statement]]
class MethodDef:
    def __init__(self, method_source):
        self.line_num = method_source[0].line_num  # used for errors
        self.method_name = method_source[2]
        if method_source[1] == InterpreterBase.VOID_DEF:
            self.return_type = Type(InterpreterBase.NOTHING_DEF)
        else:
            self.return_type = Type(method_source[1])
        self.formal_params = self.__parse_params(method_source[3])
        self.code = method_source[4]

    def get_method_name(self):
        return self.method_name

    def get_formal_params(self):
        return self.formal_params

    # returns a Type()
    def get_return_type(self):
        return self.return_type

    def get_code(self):
        return self.code

    # input params in the form of [[type1 param1] [type2 param2] ...]
    # output is a set of VariableDefs
    def __parse_params(self, params):
        formal_params = []
        for param in params:
            var_def = VariableDef(Type(param[0]), param[1])
            formal_params.append(var_def)
        return formal_params


# holds definition for a class, including a list of all the fields and their default values, all
# of the methods in the class, and the superclass information (if any)
# v2 class definition: [class classname [inherits baseclassname] [field1] [field2] ... [method1] [method2] ...]
# [] denotes optional syntax
class ClassDef:
    def __init__(self, class_source, interpreter):
        self.interpreter = interpreter
        self.name = class_source[1]
        self.class_source = class_source
        if self.__is_a_template_class(class_source):
            # don't process class at all now if it's a templated class
            return

        fields_and_methods_start_index = (
            self.__check_for_inheritance_and_set_superclass_info(class_source)
        )
        self.__create_field_list(class_source[fields_and_methods_start_index:])
        self.__create_method_list(class_source[fields_and_methods_start_index:])

    # get the classname
    def get_name(self):
        return self.name

    # get a list of FieldDef objects for all fields in the class
    def get_fields(self):
        return self.fields

    # get a list of MethodDef objects for all methods in the class
    def get_methods(self):
        return self.methods

    # returns a FieldDef object
    def get_field(self, field_name):
        if field_name not in self.field_map:
            return None
        return self.field_map[field_name]

    # returns a MethodDef object
    def get_method(self, method_name):
        if method_name not in self.method_map:
            return None
        return self.field_map[method_name]

    # returns a ClassDef object
    def get_superclass(self):
        return self.super_class

    # private helper that checks if a class is tempalted based on raw input parsed list
    def __is_a_template_class(self, class_source):
        if class_source[0] == InterpreterBase.TEMPLATE_CLASS_DEF:
            self.template_types = class_source[2]
            return True

        self.template_types = None
        return False

    # public method to check if class is templated
    def is_templated_class(self):
        return self.template_types is not None

    # given a type signature like classname@int@bool@otherclassname specializes the class by creating an instance
    # of the class with those types filled in (aka templating the class)
    def specialize_class(self, type_sig):
        types_to_use = type_sig.split(InterpreterBase.TYPE_CONCAT_CHAR)[
            1:
        ]  # classname:type1:type2 - take [type1, type2]
        if len(types_to_use) != len(self.template_types):  # +1 is for the class name
            return None  # incorrect # of type params for template
        spec_class_source = copy.deepcopy(self.class_source)
        spec_class_source[
            0
        ] = (
            InterpreterBase.CLASS_DEF
        )  # replace tclass with class so it's a regular class now
        spec_class_source[
            1
        ] = type_sig  # replace templated class name like node with node@int
        self.__specialize_class_aux(types_to_use, spec_class_source)
        return ClassDef(spec_class_source, self.interpreter)

    def __specialize_class_aux(self, types_to_use, spec_class_source):
        for pos, item in enumerate(spec_class_source):
            if type(item) is list:
                self.__specialize_class_aux(types_to_use, item)
            elif item in self.template_types:
                index = self.template_types.index(item)
                spec_class_source[pos] = types_to_use[
                    index
                ]  # change templated type to concrete type
            elif InterpreterBase.TYPE_CONCAT_CHAR in item:
                # handle case where we use the templated class type in a field or let, e.g., (field node@field_type x null)
                templated_type = item.split(InterpreterBase.TYPE_CONCAT_CHAR)
                self.__specialize_class_aux(types_to_use, templated_type)
                spec_class_source[pos] = self.__add_delimeters(
                    templated_type
                )  # change templated type to concrete type

    def __add_delimeters(self, parts):
        added_delim_list = [part + InterpreterBase.TYPE_CONCAT_CHAR for part in parts]
        added_delim_str_with_extra_delim = "".join(added_delim_list)
        return added_delim_str_with_extra_delim[:-1]  # strip out last delimeter

    def __check_for_inheritance_and_set_superclass_info(self, class_source):
        if class_source[2] != InterpreterBase.INHERITS_DEF:
            self.super_class = None
            return 2  # fields and method definitions start after [class classname ...]

        super_class_name = class_source[3]
        self.super_class = self.interpreter.get_class_def(
            super_class_name, class_source[0].line_num
        )
        return 4  # fields and method definitions start after [class classname inherits baseclassname ...]

    def __create_field_list(self, class_body):
        self.fields = []  # array of VariableDefs with default values set
        self.field_map = {}
        fields_defined_so_far = set()
        for member in class_body:
            # member format is [field typename varname default_value]
            if member[0] == InterpreterBase.FIELD_DEF:
                if member[2] in fields_defined_so_far:  # redefinition
                    self.interpreter.error(
                        ErrorType.NAME_ERROR,
                        "duplicate field " + member[2],
                        member[0].line_num,
                    )
                var_def = self.__create_variable_def_from_field(member)
                self.fields.append(var_def)
                self.field_map[member[2]] = var_def
                fields_defined_so_far.add(member[2])

    # field def: [field typename varname defvalue]
    # returns a VariableDef object that represents that field
    # TODO: document that we can now leave out the field value and we'll initialize it to the default for its type
    def __create_variable_def_from_field(self, field_def):
        # full field def with initializer value specified: (field typename fieldname initial_value)
        field_type = Type(field_def[1])
        if len(field_def) == 4:
            var_def = VariableDef(field_type, field_def[2], create_value(field_def[3]))
        else:
            var_def = VariableDef(
                field_type, field_def[2], create_default_value(field_type)
            )
        if not self.interpreter.check_type_compatibility(
            var_def.type, var_def.value.type(), True
        ):
            self.interpreter.error(
                ErrorType.TYPE_ERROR,
                "invalid type/type mismatch with field " + field_def[2],
                field_def[0].line_num,
            )
        return var_def

    def __create_method_list(self, class_body):
        self.methods = []
        self.method_map = {}
        methods_defined_so_far = set()
        for member in class_body:
            if member[0] == InterpreterBase.METHOD_DEF:
                method_def = MethodDef(member)
                if method_def.method_name in methods_defined_so_far:  # redefinition
                    self.interpreter.error(
                        ErrorType.NAME_ERROR,
                        "duplicate method " + method_def.method_name,
                        member[0].line_num,
                    )
                self.__check_method_names_and_types(method_def)
                self.methods.append(method_def)
                self.method_map[method_def.method_name] = method_def
                methods_defined_so_far.add(method_def.method_name)

    # for a given method, make sure that the paramter types are valid, return type is valid, and param names
    # are not duplicated
    def __check_method_names_and_types(self, method_def):
        if not self.interpreter.is_valid_type(
            method_def.return_type.type_name
        ) and method_def.return_type != Type(InterpreterBase.NOTHING_DEF):
            self.interpreter.error(
                ErrorType.TYPE_ERROR,
                "invalid return type for method " + method_def.method_name,
                method_def.line_num,
            )
        used_param_names = set()
        for param in method_def.formal_params:
            if param.name in used_param_names:
                self.interpreter.error(
                    ErrorType.NAME_ERROR,
                    "duplicate formal parameter " + param.name,
                    method_def.line_num,
                )
            if not self.interpreter.is_valid_type(param.type.type_name):
                self.interpreter.error(
                    ErrorType.TYPE_ERROR,
                    "invalid type for parameter " + param.name,
                    method_def.line_num,
                )
