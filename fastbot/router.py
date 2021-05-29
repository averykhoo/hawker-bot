# if isinstance(update, Update) and update.effective_message:
#     message = update.effective_message
#
#     if (
#             message.entities
#             and message.entities[0].type == MessageEntity.BOT_COMMAND
#             and message.entities[0].offset == 0
#             and message.text
#             and message.bot
#     ):
#         command = message.text[1 : message.entities[0].length]
#         args = message.text.split()[1:]
#         command_parts = command.split('@')
#         command_parts.append(message.bot.username)
#
#         if not (
#                 command_parts[0].lower() in self.command
#                 and command_parts[1].lower() == message.bot.username.lower()
#         ):
#             return None
#
#         filter_result = self.filters(update)
#         if filter_result:
#             return args, filter_result
#         return False
# return None
