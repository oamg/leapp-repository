class LuksDumpParser(object):
    """
    Class for parsing "cryptsetup luksDump" output. Given a list of lines, it
    generates a dictionary representing the dump.
    """

    class Node(object):
        """
        Helper class, every line is represented as a node. The node depth is
        based on the indentation of the line. A dictionary is produced after
        all lines are inserted.
        """

        def __init__(self, indented_line):
            self.children = []
            self.level = len(indented_line) - len(indented_line.lstrip())
            self.text = indented_line.strip()

        def add_children(self, nodes):
            # NOTE(pstodulk): it's expected that nodes are non-empty list and
            # having it empty is an error if it happens. So keeping a hard crash
            # for now as having an empty list it's hypothetical now and I would
            # probably end with en error anyway if discovered.
            childlevel = nodes[0].level
            while nodes:
                node = nodes.pop(0)
                if node.level == childlevel:  # add node as a child
                    self.children.append(node)
                elif node.level > childlevel:  # add nodes as grandchildren of the last child
                    nodes.insert(0, node)
                    self.children[-1].add_children(nodes)
                elif node.level <= self.level:  # this node is a sibling, no more children
                    nodes.insert(0, node)
                    return

        def as_dict(self):
            if len(self.children) > 1:
                children = [node.as_dict() for node in self.children]

                return {self.text: LuksDumpParser._merge_list(children)}
            if len(self.children) == 1:
                return {self.text: self.children[0].as_dict()}
            return self.text

    @staticmethod
    def _count_type(elem_list, elem_type):
        """ Count the number of items of elem_type inside the elem_list """
        return sum(isinstance(x, elem_type) for x in elem_list)

    @staticmethod
    def _merge_list(elem_list):
        """
        Given a list of elements merge them into a single element. If all
        elements are strings, concatenate them into a single string. When all
        the elements are dictionaries merge them into a single dictionary
        containing the keys/values from all of the dictionaries.
        """

        dict_count = LuksDumpParser._count_type(elem_list, dict)
        str_count = LuksDumpParser._count_type(elem_list, str)

        result = elem_list
        if dict_count == len(elem_list):
            result = {}
            for element in elem_list:
                result.update(element)
        elif str_count == len(elem_list):
            result = "".join(elem_list)

        return result

    @staticmethod
    def _find_single_str(elem_list):
        """ If the list contains exactly one string return it or return None otherwise. """

        result = None

        for elem in elem_list:
            if isinstance(elem, str):
                if result is not None:
                    # more than one strings in the list
                    return None
                result = elem

        return result

    @staticmethod
    def _fixup_type(elem_list, type_string):
        single_string = LuksDumpParser._find_single_str(elem_list)

        if single_string is not None:
            elem_list.remove(single_string)
            elem_list.append({type_string: single_string})

    @staticmethod
    def _fixup_section(section, type_string):
        for key, value in section.items():
            LuksDumpParser._fixup_type(value, type_string)
            section[key] = LuksDumpParser._merge_list(section[key])

    @staticmethod
    def _fixup_dict(parsed_dict):
        """ Various fixups of the parsed dictionary """

        if "Version" not in parsed_dict:
            return
        if parsed_dict["Version"] == "1":
            for i in range(8):
                keyslot = "Key Slot {}".format(i)

                if keyslot not in parsed_dict:
                    continue

                if parsed_dict[keyslot] in ["ENABLED", "DISABLED"]:
                    parsed_dict[keyslot] = {"enabled": parsed_dict[keyslot] == "ENABLED"}

                if not isinstance(parsed_dict[keyslot], list):
                    continue

                enabled = None
                if "ENABLED" in parsed_dict[keyslot]:
                    enabled = True
                    parsed_dict[keyslot].remove("ENABLED")
                if "DISABLED" in parsed_dict[keyslot]:
                    enabled = False
                    parsed_dict[keyslot].remove("DISABLED")
                parsed_dict[keyslot] = LuksDumpParser._merge_list(parsed_dict[keyslot])
                if enabled is not None:
                    parsed_dict[keyslot]["enabled"] = enabled
        elif parsed_dict["Version"] == "2":
            for section in ["Keyslots", "Digests", "Data segments", "Tokens"]:
                if section in parsed_dict:
                    LuksDumpParser._fixup_section(parsed_dict[section], "type")

    @staticmethod
    def _fixup_dump(dump):
        """
        Replace tabs with spaces, for lines with colon a move the text
        after column on new line with the indent of the following line.
        """

        dump = [line.replace("\t", " "*8).replace("\n", "") for line in dump]
        newdump = []

        for i, line in enumerate(dump):
            if not line.strip():
                continue

            if ':' in line:
                first_half = line.split(":")[0]
                second_half = ":".join(line.split(":")[1:]).lstrip()

                current_level = len(line) - len(line.lstrip())
                if i+1 < len(dump):
                    next_level = len(dump[i+1]) - len(dump[i+1].lstrip())
                else:
                    next_level = current_level

                if next_level > current_level:
                    second_half = " " * next_level + second_half
                else:
                    second_half = " " * (current_level + 8) + second_half

                newdump.append(first_half)
                if second_half.strip():
                    newdump.append(second_half)
            else:
                newdump.append(line)

        return newdump

    @staticmethod
    def parse(dump):
        """
        Parse the output of "cryptsetup luksDump" command into a dictionary.

        :param dump: List of output lines of luksDump
        :returns: Parsed dictionary
        """

        root = LuksDumpParser.Node('root')

        nodes = []
        for line in LuksDumpParser._fixup_dump(dump):
            nodes.append(LuksDumpParser.Node(line))

        root.add_children(nodes)
        root = root.as_dict()['root']

        if isinstance(root, list):
            result = {}
            for child in root:
                if isinstance(child, str):
                    child = {child: {}}
                result.update(child)
            root = result

        LuksDumpParser._fixup_dict(root)
        return root
