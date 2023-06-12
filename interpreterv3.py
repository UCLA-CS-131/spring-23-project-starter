from classv3 import ClassDef
from intbase import InterpreterBase, ErrorType
from bparser import BParser
from objectv3 import ObjectDef
from type_valuev3 import TypeManager

# need to document that template classes can't be base or derived classes and students won't be tested on that


# Main interpreter class
class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output

    # run a program, provided in an array of strings, one string per line of source code
    # usese the provided BParser class found in parser.py to parse the program into lists
    def run(self, program):
        status, parsed_program = BParser.parse(program)
        if not status:
            super().error(
                ErrorType.SYNTAX_ERROR, f"Parse error on program: {parsed_program}"
            )
        self.__add_all_class_types_to_type_manager(parsed_program)
        self.__map_class_names_to_class_defs(parsed_program)

        # instantiate main class
        invalid_line_num_of_caller = None
        self.main_object = self.instantiate(
            InterpreterBase.MAIN_CLASS_DEF, invalid_line_num_of_caller
        )

        # call main function in main class; return value is ignored from main
        self.main_object.call_method(
            InterpreterBase.MAIN_FUNC_DEF, [], False, invalid_line_num_of_caller
        )

        # program terminates!

    # user passes in the line number of the statement that performed the new command so we can generate an error
    # if the user tries to new an class name that does not exist. This will report the line number of the statement
    # with the new command
    # class_name might be a simple classname like Person or a templated classname like list@Person
    def instantiate(self, class_name, line_num_of_statement):
        class_def = self.__get_class_def_from_class_name(class_name)
        if class_def is None:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Invalid class or templated class type {class_name}",
                line_num_of_statement,
            )

        obj = ObjectDef(
            self, class_def, None, self.trace_output
        )  # Create an object based on this class definition
        return obj

    # returns a ClassDef object - only used for non-templated classes to locate the base class
    def get_class_def(self, class_name, line_number_of_statement):
        if class_name not in self.class_index:
            super().error(
                ErrorType.NAME_ERROR,
                f"No class named {class_name} found",
                line_number_of_statement,
            )
        return self.class_index[class_name]

    # returns a bool
    def is_valid_type(self, typename):
        return self.type_manager.is_valid_type(typename)

    # returns a bool
    def is_a_subtype(self, suspected_supertype, suspected_subtype):
        return self.type_manager.is_a_subtype(suspected_supertype, suspected_subtype)

    # typea and typeb are Type objects; returns true if the two type are compatible
    # for assignments typea is the type of the left-hand-side variable, and typeb is the type of the
    # right-hand-side variable, e.g., (set person_obj_ref (new teacher))
    def check_type_compatibility(self, typea, typeb, for_assignment=False):
        return self.type_manager.check_type_compatibility(typea, typeb, for_assignment)

    # pass in a regular class name (e.g., person) or templated class name (e.g. list@int)
    def __get_class_def_from_class_name(self, class_type):
        if not self.type_manager.is_valid_type(class_type):
            return None

        if InterpreterBase.TYPE_CONCAT_CHAR in class_type:
            parts = class_type.split(InterpreterBase.TYPE_CONCAT_CHAR)
            class_name = parts[0]
        else:
            class_name = class_type

        # we know it's in the class index or else the call to is_valid_type above would have failed
        class_def = self.class_index[class_name]
        if class_def.is_templated_class():
            class_def = class_def.specialize_class(
                class_type
            )  # class_type e.g., node@int
        return class_def

    def __map_class_names_to_class_defs(self, program):
        self.class_index = {}
        for item in program:
            if (
                item[0] == InterpreterBase.CLASS_DEF
                or item[0] == InterpreterBase.TEMPLATE_CLASS_DEF
            ):
                if item[1] in self.class_index:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Duplicate class name {item[1]}",
                        item[0].line_num,
                    )
                self.class_index[item[1]] = ClassDef(item, self)

    # [class classname inherits superclassname [items]]
    def __add_all_class_types_to_type_manager(self, parsed_program):
        self.type_manager = TypeManager()
        for item in parsed_program:
            class_name = item[1]
            superclass_name = None
            if item[0] == InterpreterBase.CLASS_DEF:
                if item[2] == InterpreterBase.INHERITS_DEF:
                    superclass_name = item[3]
                self.type_manager.add_class_type(class_name, superclass_name, 0)
            if item[0] == InterpreterBase.TEMPLATE_CLASS_DEF:
                type_params = item[2]
                self.type_manager.add_class_type(
                    class_name, superclass_name, len(type_params)
                )
