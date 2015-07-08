def trimType(typeDesc):
	return typeDesc.rpartition(".")[2]

# Parse a method or constructor into tab completion text, type hint and verbose hint
def parseMethod(access, methodName, args, returntype, asCtor):
	verboseHintText = " ".join(access)
	methodText = methodName+"("

	if asCtor:
		typeHint = "Class ("
	else:
		typeHint = "("

	count = 1
	for arg in args:
		if type(arg) is str:
			break

		if count>1:
			methodText += ", "
			typeHint += ", "

		argName = arg["Name"]
		
		if arg["IsOut"]:
			methodText += "out ${" + str(count) + ":" + argName + "}"
			typeHint += "out "
		else:
			methodText += "${" + str(count) + ":" + argName + "}"

		typeHint += trimType(arg["ArgType"]) + " " + argName

		count += 1

	if asCtor:
		typeHint += ")"
	else:
		typeHint += "):" + trimType(returntype)
	methodText += ")"

	return (methodText, typeHint, verboseHintText)

def parseUXSuggestion(wordAtCaret, suggestion, suggestedUXNameSpaces, useShortCompletion, foldUXNameSpaces):
	isNs = False
	outText = suggestion["Suggestion"]
	hintText = suggestion["ReturnType"]
	if foldUXNameSpaces and wordAtCaret != ":":
		colonIdx = outText.find(":") + 1
		if colonIdx > 0:
			nsname = outText[0:colonIdx]
			hinted = nsname in suggestedUXNameSpaces
			isNs = True
			if not hinted:
				suggestedUXNameSpaces.append(nsname)
				outText = nsname
				hintText = nsname[0:len(nsname)-1]
			else:
				return None

	if not isNs and (not useShortCompletion):
		hintText += '="${1}"'

	return (outText, hintText)