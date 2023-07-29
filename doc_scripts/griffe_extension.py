import ast
import re
from griffe import Extension, Object, ObjectNode

class RegexUrl(Extension):
    IGNORE = ['sg'] #
    
    def regex_replace(self, input_string, regex_pattern, prefix):
        compiled_pattern = re.compile(regex_pattern)

        def replace_function(match):
            parts = match.group(1).split('.')
            if any(parts[0].startswith(prefix) for prefix in self.IGNORE):
                return match.group(0)

            # get text section of url, we will only use the last obj
            text = parts[-1]
            
            fn_suffix = ""
            if match.group(2):
                # pass () as html encoding
                fn_suffix = "&#40;&#41;"
            complete_path = prefix + match.group(1)
            return f"[{text}{fn_suffix}][{complete_path}]"

        output_string = compiled_pattern.sub(replace_function, input_string)
        return output_string    
    
    def on_instance(self, node: ast.AST | ObjectNode, obj: Object) -> None:
        if obj.docstring:
            # regex pattern matches a valid non-private class name or function, with or without a '()' at the end
            regex_pattern = r'\`([A-Za-z][A-Za-z0-9_.]*)(\(\))*\`'
            obj.docstring.value = self.regex_replace(obj.docstring.value, regex_pattern, "pysimplesql.pysimplesql.")