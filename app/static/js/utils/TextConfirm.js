// Simple, inline yes/no confirmation prompt.
import _ from './I18n';
import InlinePrompt from './InlinePrompt';

function TextConfirm(the_element, yesfunc, question, nofunc){
  InlinePrompt({
    text: question || _("Are you sure?"),
    options: [
      [_("yes"), yesfunc],
      [_("no"), nofunc]
    ],
    elem: the_element,
  });
}

export default TextConfirm;
