Alrighty, tutorial time. 

The base element of the condition for a response is the Condition. The following exist:
- **contains: "string"** e.g. **contains: "foo"** - note that the quotation marks are mandatory. I have not bothered to implement any form of escaping characters, so you can't have a " inside a string. Conditions are case-insensitive.  
- **onein: number** e.g. **onein: 4**. Adds a chance for a message to be displayed or not.
- **authoredby: "name"** e.g. **authoredby: "alice"** - checks message author. Uses their full discord name, not their server nickname. Note that names are also case-insensitive right now.  
 - **containsword: "string"** e.g. **containsword: "foo"** - basically the same as contains, but doesn't get triggered by words inside other words

The colons are actually optional, onein 4 works as well as onein: 4.

If you have a message that'll trigger on a common word, I recommend using onein. This is because all authors are subject to an author-specific ratelimit. As your messages trigger, a % failure chance is imposed on *all messages authored by you*, gradually relaxing over time. 

You can combine base elements using boolean logic. **&** and **|** mean **and** and **or** respectively. When mixing & and |, the result can be ambiguous, and must be disambiguated by using **()**. For example, you have to write contains: "foo" & (contains "bar" | onein: 4). 

To implement **not**, use **~** or **!**