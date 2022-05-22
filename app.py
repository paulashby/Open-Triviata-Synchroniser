import sys
from helpers import next_category, level_counts, process_category
def main():

    # Start with the next incomplete category
    category = next_category()

    while category:

        category_id = category['id']

        # Get number of questions already processed for each difficulty level
        already_done = level_counts(category_id)
        to_do_list = {
            'category': category_id,
            'total': category['total_question_count'],
            'levels': {}
        }
        
        for level, done in already_done.items():
            # Check for incomplete difficulty levels
            available_questions = category[f"total_{level}_question_count"]

            if done < available_questions:
                # There are more questions to process for this level - place on to_do_list
                to_do_list['levels'][level] = available_questions

        process_category(to_do_list)

        category = next_category(category_id + 1)

    print("SUCCESS: all questions have been processed :)")
    sys.exit(0)

if __name__ == "__main__":
    main()