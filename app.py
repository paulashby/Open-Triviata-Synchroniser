from helpers import get_session_token, reset_session_token, api_request, get_curr_cat_q_count

def main():
    
    curr_cat_details = get_curr_cat_q_count()

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