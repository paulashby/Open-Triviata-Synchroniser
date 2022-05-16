from helpers import get_session_token, reset_session_token, api_request, current_category, question_breakdown, questions_in
def main():

    QUERY_MAX = 50

    global_question_count = question_breakdown()

    """
    Get details of current category: 
    category_id
    category_question_count
    - total_question_count
    - total_easy_question_count
    - total_medium_question_count
    - total_hard_question_count


    check boolean q


    """
    category_id = current_category()
    category_info = question_breakdown(current_category())
    questions_done = questions_in(category_id)
    
    print(f"questions_done: {questions_done}")

    
    """
    current_category_info = {
        'category_id': 9, 
        'category_question_count': {
            'total_question_count': 298, 
            'total_easy_question_count': 116, 
            'total_medium_question_count': 123, 
            'total_hard_question_count': 59}
        },
    
    Have we processed any/all of the questions in this category?
    NOTE: Need to perform all our checks here on current_category_info, 
    as this this be updated if we change category in the first clause
    All - do next category - 
        question_count(current_category_info['category_id'] + 1))

        if not cat_id in global_question_count.keys():


        if there's no next category, we're done and the programme can end
        so that's 

        if not cat_id in global_question_count.keys():
        there is no else here - we just move on to
    None - do all
    Some -
      - which difficulty levels (DLs) are lacking?
      - Redo those DLs

    num_full_calls = floor(current_category_info/QUERY_MAX)
    final_call_qty = current_category_info % QUERY_MAX
    """

    # Get 

    # get the id and the count of the highest-numbered category from opentriviata

    # get the number of available entries from the API

    # https://opentdb.com/api_count.php?category=9

    # Return eg
    """
    {
        "category_id": 9,
        "category_question_count": {
            "total_question_count": 298,
            "total_easy_question_count": 116,
            "total_medium_question_count": 123,
            "total_hard_question_count": 59
        }
    }
    """
    
    # if our count matches total_question_count
        # - move on to next category
    
    # elif our count is 0
        # - scrape_category(category_id)

    # else (our count is lower than total_question_count) either:
        # - new questions have been added
        # - something has gone wrong and we failed to complete the category on our previous session
        # In either case, we need to:
        
        # - check the counts for each level of difficulty (LOD), 
            # if we're short in all
                # - delete all questions for this category, remove it from the categories table and start again 
            # else 
                # - we're only short in some, delete all questions for each under-populated LOD and redo it - 
                # (will also need to delete from answers table AND category if we end up removing all)
                # - we are definitely short in at least one, since our category question count is lower than total_question_count



if __name__ == "__main__":
    main()