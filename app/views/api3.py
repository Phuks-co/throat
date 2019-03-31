""" API endpoints. """

from flask import Blueprint, jsonify
from peewee import JOIN
from .. import misc
from ..models import Sub, User, SubPost, SubPostComment

API = Blueprint('apiv3', __name__)


@API.route('/getPost/<int:pid>', methods=['get'])
def get_post(pid):
    """Returns information for a post """
    # Same as v2 API but `content` is HTML instead of markdown

    base_query = SubPost.select(SubPost.nsfw, SubPost.content, SubPost.pid, SubPost.title, SubPost.posted, SubPost.score, SubPost.deleted,
                                SubPost.thumbnail, SubPost.link, User.name.alias('user'), Sub.name.alias('sub'), SubPost.flair, SubPost.edited,
                                SubPost.comments, SubPost.ptype, User.status.alias('userstatus'), User.uid, SubPost.upvotes, SubPost.downvotes)
    base_query = base_query.join(User, JOIN.LEFT_OUTER).switch(SubPost).join(Sub, JOIN.LEFT_OUTER)

    post = base_query.where(SubPost.pid == pid).dicts()

    if not post.count():
        return jsonify(status="error", error="Post does not exist")

    post = post[0]
    post['deleted'] = True if post['deleted'] != 0 else False

    if post['deleted']:  # Clear data for deleted posts
        post['content'] = None
        post['link'] = None
        post['uid'] = None
        post['user'] = '[Deleted]'
        post['thumbnail'] = None
        post['edited'] = None

    if post['content']:
        post['content'] = misc.our_markdown(post['content'])

    if post['userstatus'] == 10:
        post['user'] = '[Deleted]'
        post['uid'] = None
    del post['userstatus']

    return jsonify(status='ok', post=post)


def get_comment_tree(comments, root=None, only_after=None):
    """ Returns a fully paginated and expanded comment tree.

    Parameters:
        comments: bare list of comments (only cid and parentcid)
        root: if present, the root comment to start building the tree on
        only_after: removes all siblings of `root` after the cid on its value

    TODO: Move to misc and implement globally
    """
    def build_tree(tuff, root=None):
        """ Builds a comment tree """
        res = []
        for i in tuff[::]:
            if i['parentcid'] == root:
                tuff.remove(i)
                i['children'] = build_tree(tuff, root=i['cid'])
                res.append(i)
        return res

    # 2 - Build bare comment tree
    comment_tree = build_tree(list(comments))

    # 2.1 - get only a branch of the tree if necessary
    if root:
        def select_branch(comments, root):
            """ Finds a branch with a certain root and returns a new tree """
            for i in comments:
                if i['cid'] == root:
                    return i
                k = select_branch(i['children'], root)
                if k:
                    return k
        comment_tree = select_branch(comment_tree, root)
        if comment_tree:
            comment_tree = comment_tree['children']
        else:
            return []
    # 3 - Trim tree (remove all children of depth=3 comments, all siblings after #5
    cid_list = []
    trimmed = False
    def recursive_check(tree, depth=0, trimmed=None):
        """ Recursively checks tree to apply pagination limits """
        or_len = len(tree)
        if only_after and not trimmed:
            imf = list(filter(lambda i: i['cid'] == only_after, tree))
            if imf:
                try:
                    tree = tree[tree.index(imf[0]) + 1:]
                except IndexError:
                    return []
                or_len = len(tree)
                trimmed = True
        if depth > 3:
            return [{'cid': None, 'more': len(tree)}] if tree else []
        if (len(tree) > 5 and depth > 0) or (len(tree) > 10):
            tree = tree[:6] if depth > 0 else tree[:11]
            tree.append({'cid': None, 'key': tree[-2]['cid'], 'more': or_len - len(tree)})

        for i in tree:
            if not i['cid']:
                continue
            cid_list.append(i['cid'])
            i['children'] = recursive_check(i['children'], depth+1)

        return tree

    comment_tree = recursive_check(comment_tree, trimmed=trimmed)

    # 4 - Populate the tree (get all the data and cram it into the tree)
    expcomms = SubPostComment.select(SubPostComment.cid, SubPostComment.content, SubPostComment.lastedit,
                                     SubPostComment.score, SubPostComment.status, SubPostComment.time, SubPostComment.pid,
                                     User.name.alias('username'), SubPostComment.uid, # SubPostCommentVote.positive
                                     User.status.alias('userstatus'), SubPostComment.upvotes, SubPostComment.downvotes)
    expcomms = expcomms.join(User, on=(User.uid == SubPostComment.uid)).switch(SubPostComment)
    #expcomms = expcomms.join(SubPostCommentVote, JOIN.LEFT_OUTER, on=((SubPostCommentVote.uid == current_user.get_id()) & (SubPostCommentVote.cid == SubPostComment.cid)))
    expcomms = expcomms.where(SubPostComment.cid << cid_list).dicts()

    commdata = {x['cid']: x for x in expcomms}

    def recursive_populate(tree):
        """ Expands the tree with the data from `commdata` """
        populated_tree = []
        for i in tree:
            if not i['cid']:
                populated_tree.append(i)
                continue
            comment = commdata[i['cid']]
            comment['content'] = misc.our_markdown(comment['content'])
            comment['children'] = recursive_populate(i['children'])
            populated_tree.append(comment)
        return populated_tree

    comment_tree = recursive_populate(comment_tree)
    return comment_tree


@API.route('/getPost/<int:pid>/comments', methods=['get'])
def get_post_comments(pid):
    """ Returns comment tree

    Return dict format:
    "comments": [
        {"cid": ...,
            "content": ...,
            "children": [
                {"cid": ..., ...},
                ...
                {"cid": null}
            ]
        },
        ....
        {"cid": null, "key": ...} <-- "Load more comments" (siblings) mark
    ]

    Upon reaching a cid=null comment, return link to get_post_comment_children with
    cid of the parent comment or 0 if it is a root comment and lim equal to the key
    provided or absent if no key is provided
    """
    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(status='error', error="Post does not exist")

    # 1 - Fetch all comments (only cid and parentcid)
    comments = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid).where(SubPostComment.pid == post.pid).order_by(SubPostComment.score.desc()).dicts()
    if not comments.count():
        return jsonify(status='ok', comments=[])

    comment_tree = get_comment_tree(comments)
    return jsonify(status='ok', comments=comment_tree)


@API.route('/getPost/<int:pid>/comments/children/<cid>/<lim>', methods=['get'])
@API.route('/getPost/<int:pid>/comments/children/<cid>', methods=['get'], defaults={'lim': ''})
def get_post_comment_children(pid, cid, lim):
    """ if lim is not present, load all children for cid.
    if lim is present, load all comments after (???) index lim

    NOTE: This is a crappy solution since comment sorting might change when user is
    seeing the page and we might end up re-sending a comment (will show as duplicate).
    This can be solved by the front-end checking if a cid was already rendered, but it
    is a horrible solution
    """
    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(status='error', error='Post does not exist')
    if cid != '0':
        try:
            root = SubPostComment.get(SubPostComment.cid == cid)
            if root.pid_id != post.pid:
                return jsonify(status='error', error='Comment does not belong to the given post')
        except SubPostComment.DoesNotExist:
            return jsonify(status='error', error='Post does not exist')

    comments = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid).where(SubPostComment.pid == pid).order_by(SubPostComment.score.desc()).dicts()
    if not comments.count():
        return jsonify(status='ok', comments=[])

    if lim:
        if cid == '0':
            cid = None
        comment_tree = get_comment_tree(comments, cid, lim)
    elif cid != '0':
        comment_tree = get_comment_tree(comments, cid)
    else:
        return jsonify(status='error', error='Illegal comment id')
    return jsonify(status='ok', comments=comment_tree)
